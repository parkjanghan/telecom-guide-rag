"""Display provenance without promoting routing metadata to policy evidence."""
from urllib.parse import urlparse

LABELS={
 'official_faq':'공식 FAQ',
 'service_guide':'공식 서비스 가이드',
 'product_detail':'공식 상품 안내',
 'discount_guide':'공식 할인 안내',
 'payment_benefit_guide':'공식 제휴 혜택 안내',
 'terms_pdf':'공식 약관 PDF',
 'official_pdf':'공식 PDF 문서',
 'official_web':'공식 웹 문서',
}


def evidence_presentation(evidence,parent=None):
    parent=parent or {};meta=parent.get('meta',{})
    path=evidence.get('source_path') or parent.get('path','')
    title=evidence.get('title') or parent.get('title','')
    raw=evidence.get('source_type') or meta.get('source_type','')
    url=evidence.get('source_url','');parsed=urlparse(url)
    pdf=(raw in {'pdf','terms_pdf','official_pdf'} or '/terms/' in path or parsed.path.lower().endswith('.pdf') or bool(evidence.get('source_pages')) or bool(meta.get('source_pages')))
    if pdf:
        kind='terms_pdf' if '약관' in title or raw=='terms_pdf' else 'official_pdf'
    elif raw=='official_faq' or '/faq/' in path or parsed.hostname=='ermsweb.kt.com':kind='official_faq'
    elif raw=='service_guide' or '/service_guides/' in path or '/serviceinfo/' in parsed.path:kind='service_guide'
    elif '/payment_benefits/' in path:kind='payment_benefit_guide'
    elif '/discounts/' in path:kind='discount_guide'
    elif raw=='product_detail' or any('/'+folder+'/' in path for folder in ['bundles','mobile_plans']) or parsed.hostname in {'product.kt.com','m.product.kt.com'}:kind='product_detail'
    else:kind='official_web'
    live=evidence.get('role')=='external_live'
    return {'source_type':kind,'source_type_label':LABELS[kind],
            'source_format':'PDF' if pdf else '웹 페이지',
            'source_origin':'external_lookup' if live else 'saved_document',
            'source_origin_label':'추가 조회한 공식 자료' if live else '저장한 공식 자료'}


def topic_context(topics):
    return [{'item_id':t['item_id'],'name':t['name'],'summary':t.get('summary',''),
             'scope':t.get('scope',''),'source_type':'topic_metadata',
             'source_type_label':'탐색용 주제 메타데이터','is_policy_evidence':False}
            for t in topics]
