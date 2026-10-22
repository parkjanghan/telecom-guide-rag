import re


def original_quote(quote, text):
    """Only normalize whitespace, then return the exact original character span."""
    if quote in text:return quote
    chars=[];positions=[]
    for match in re.finditer(r'\s+|\S',text):
        token=' ' if match.group().isspace() else match.group()
        chars.append(token);positions.append((match.start(),match.end()))
    wanted=re.sub(r'\s+',' ',quote).strip()
    normalized=''.join(chars)
    start=normalized.find(wanted)
    if not wanted or start<0:return None
    return text[positions[start][0]:positions[start+len(wanted)-1][1]]


def validate_answer(data, sources):
    if not isinstance(data, dict) or set(data) != {'claims','follow_up'}:
        raise ValueError('answer_schema_invalid')
    if not isinstance(data['follow_up'], str) or len(data['follow_up']) > 1200:
        raise ValueError('follow_up_invalid')
    if not isinstance(data['claims'], list) or len(data['claims']) > 10:
        raise ValueError('claims_invalid')
    for claim in data['claims']:
        if not isinstance(claim, dict) or set(claim) != {'text','inferred','citations'}:
            raise ValueError('claim_schema_invalid')
        if not isinstance(claim['text'], str) or not claim['text'].strip() or len(claim['text']) > 3000 or type(claim['inferred']) is not bool:
            raise ValueError('claim_invalid')
        if claim['inferred'] and '확인한 문서에는 이 결론이 직접 명시되어 있지 않습니다.' not in claim['text']:
            raise ValueError('inference_disclosure_missing')
        if not isinstance(claim['citations'], list) or not claim['citations']:
            raise ValueError('citation_missing')
        for cite in claim['citations']:
            if not isinstance(cite, dict) or set(cite) != {'id','quote'}:
                raise ValueError('citation_invalid')
            sid, quote = cite['id'], cite['quote']
            if not isinstance(sid,str) or sid not in sources or not isinstance(quote,str) or len(quote.strip()) < 8:
                raise ValueError('citation_quote_invalid')
            exact=original_quote(quote,sources[sid]['text'])
            if exact is None:raise ValueError('citation_quote_invalid')
            cite['quote']=exact
    return data

