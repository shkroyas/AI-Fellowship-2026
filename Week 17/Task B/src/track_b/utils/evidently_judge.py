"""Live Evidently judges plus deterministic regression checks, joined by case ID."""
import asyncio
import json
import re
import unicodedata
from pathlib import Path
import pandas as pd
from evidently import Dataset, DataDefinition, Report
from evidently.descriptors import LLMJudge
from evidently.llm.templates import BinaryClassificationPromptTemplate
from evidently.llm.utils.wrapper import OpenAIOptions, OpenAIWrapper, LLMResult, llm_provider
from evidently.presets import TextEvals
from evidently.tests import eq


@llm_provider('bounded_openai', None)
class BoundedJudgeWrapper(OpenAIWrapper):
    """Keep live judge calls sequential, bounded, and provider-rate aware."""
    def get_batch_size(self):
        return 1

    async def complete(self, messages, seed=None):
        import openai
        for attempt in range(4):
            try:
                response = await self.client.with_options(max_retries=0, timeout=45).chat.completions.create(
                    model=self.model, messages=[{'role': m.role, 'content': m.content} for m in messages],
                    temperature=0, max_completion_tokens=768,
                    extra_body={'reasoning_effort': 'low'} if self.model.startswith('openai/gpt-oss') else {})
                await asyncio.sleep(6)
                if not response.choices:
                    raise RuntimeError("Judge provider returned no choices (upstream error)")
                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError('Empty judge response')
                return LLMResult(content, response.usage.prompt_tokens, response.usage.completion_tokens)
            except openai.RateLimitError:
                if attempt == 3:
                    raise
                await asyncio.sleep(30)


def score_numeric(response, expected, tolerance=1e-6):
    numbers = re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)", response)
    # Reject contradictions, including an incorrect answer followed by the reference.
    if re.search(r"\b(not|incorrect|wrong|cannot)\b", response, re.I):
        return False
    return bool(numbers) and abs(float(numbers[-1]) - expected) <= tolerance


def score_response_v2(response, golden):
    response = unicodedata.normalize("NFKC", response).replace("‐", "-").replace("‑", "-").replace("–", "-")
    if not response.strip() or response.lower().startswith('error:'):
        return False, 'Missing/error response'
    kind = golden.get('check_type')
    if kind == 'numeric':
        return score_numeric(response, golden['expected_number']), 'Final numeric answer comparison'
    if kind == 'datetime':
        from dateutil.parser import parse
        expected = golden.get('expected_date')
        if not expected or re.search(r"\b(cannot|can't|unable|not the (current )?date)\b", response, re.I):
            return False, 'Missing date evidence or refusal'
        months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
        patterns = [r'\b\d{4}-\d{2}-\d{2}\b',
                    rf'\b{months}\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}}\b',
                    rf'\b\d{{1,2}}(?:st|nd|rd|th)?\s+{months}[,]?\s+\d{{4}}\b']
        candidates = [match.group() for pattern in patterns for match in re.finditer(pattern, response, re.I)]
        try:
            dates = [parse(value).date().isoformat() for value in candidates]
        except ValueError:
            return False, 'Invalid date in response'
        return bool(dates) and all(value == expected for value in dates), 'Parsed date matches captured tool date'
    words = golden.get('must_contain', [])
    if not words:
        return False, 'No deterministic criteria defined'
    denied = re.search(r"\b(has no|no retrieval|no generation|never uses|does not use|doesn't use)\b", response, re.I)
    return all(w.lower() in response.lower() for w in words) and not bool(denied), 'Required concepts and negation check'


def join_cases(results, golden):
    ids = [r.get('golden_id') for r in results]
    expected = {g['id'] for g in golden}
    if len(ids) != len(set(ids)) or any(i not in expected for i in ids):
        raise ValueError('Duplicate, absent, or unknown result IDs')
    lookup = {r['golden_id']: r for r in results}
    rows = []
    for g in golden:
        result = lookup.get(g['id'], {})
        evidence = json.dumps([step for step in result.get('steps', []) if step.get('action') == 'tool_call'], ensure_ascii=False)
        scoring = dict(g)
        target = g['target']
        required_tool = ''
        if g['id'] == 'calculator_pct':
            scoring.update(check_type='numeric', expected_number=51.0)
            required_tool = 'calculator'
        elif g['id'] == 'datetime_now':
            required_tool = 'get_current_datetime'
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', evidence)
            scoring.update(check_type='datetime', expected_date=dates[0] if dates else None)
            target = 'Answer using the date and timezone in this captured tool evidence: ' + evidence
        else:
            scoring['check_type'] = 'rag' if g['id'].startswith('rag') else 'general'
        passed, reason = score_response_v2(result.get('response', ''), scoring)
        rows.append(dict(golden_id=g['id'], query=g['query'], new_response=result.get('response', ''),
                         target_response=target, tool_evidence=evidence, required_tool=required_tool,
                         deterministic_pass=passed, deterministic_reason=reason,
                         result_found=bool(result), terminated=result.get('stopped_reason') == 'model_answered'))
    return pd.DataFrame(rows)


class EvidentlyJudge:
    def __init__(self, reports_dir=None):
        self.reports_dir = Path(reports_dir or Path(__file__).resolve().parents[3] / 'reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, version, results, golden):
        from src.track_b.assistant.config import settings
        df = join_cases(results, golden)
        keys = settings.groq_keys()
        if settings.llm_provider == 'groq':
            if not keys:
                raise RuntimeError('A configured Groq key is required for live judge evaluation')
            key, url, model = keys[0], 'https://api.groq.com/openai/v1', settings.groq_model
        else:
            key, url, model = settings.openrouter_api_key, 'https://openrouter.ai/api/v1', settings.openrouter_model
        criteria = {
            'correctness': 'Question: {query}\nReference answer: {target_response}\nPASS only if the response answers the question correctly and consistently with the reference. Equivalent wording is acceptable. Reject contradictions, refusals, empty answers and fabricated dates.',
            'grounding': 'Question: {query}\nActual tool trace: {tool_evidence}\nRequired tool (empty means optional): {required_tool}\nPASS only if required tools were successfully called and the answer faithfully uses their results. Reject fabricated tool use, unsupported source claims, contradictions and treating failed tools as evidence. For conceptual questions without required tools, an accurate general answer without fabricated sources may pass.',
        }
        descriptors = []
        for name, criterion in criteria.items():
            descriptors.append(LLMJudge(provider='bounded_openai', model=model, alias=name,
                input_columns={c: c for c in ['query', 'target_response', 'tool_evidence', 'required_tool']} | {'new_response': 'input'},
                template=BinaryClassificationPromptTemplate(criteria=criterion,
                    target_category='PASS', non_target_category='FAIL', uncertainty='non_target',
                    include_reasoning=True), tests=[eq('PASS', column=name)]))
        dataset = Dataset.from_pandas(df, data_definition=DataDefinition(
            text_columns=['query', 'new_response', 'target_response', 'tool_evidence', 'required_tool']),
            descriptors=descriptors, options=[OpenAIOptions(api_key=key, api_url=url, rpm_limit=10)])
        evaluated = dataset.as_dataframe()
        for name in criteria:
            if name not in evaluated or not evaluated[name].isin(['PASS', 'FAIL']).all():
                raise RuntimeError(f'Judge {name} returned missing or invalid verdicts')
        evaluated['passed'] = (evaluated['correctness'].eq('PASS') & evaluated['grounding'].eq('PASS')
                               & evaluated['deterministic_pass'] & evaluated['result_found'] & evaluated['terminated'])
        snapshot = Report(metrics=[TextEvals()], include_tests=True).run(current_data=dataset)
        snapshot.save_html(str(self.reports_dir / f'evidently_report_{version}.html'))
        snapshot.save_json(str(self.reports_dir / f'evidently_snapshot_{version}.json'))
        evaluated.to_json(self.reports_dir / f'verdicts_{version}.json', orient='records', indent=2)
        return dict(pct_tests_passed=float(evaluated['passed'].mean()), total_tests=len(evaluated),
                    correct=int(evaluated['passed'].sum()), judge_model=model,
                    judge_checks=list(criteria), judge_agreement=None,
                    agreement_note='Not measured: no independent human labels supplied',
                    per_case_verdicts=json.loads(evaluated.to_json(orient='records')))
