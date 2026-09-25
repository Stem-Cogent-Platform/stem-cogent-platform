"""Versioned, cited claim screening. Suggestions require human approval."""
from __future__ import annotations

import re

RULES_VERSION = '2026-09-25-v1'
CBN_SOURCE = 'https://www.cbn.gov.ng/out/2019/ccd/cbn%20consumer%20protection%20regulations.pdf'
SEC_SOURCE = 'https://sec.gov.ng/for-investors/keep-track-of-circulars/public-notice-unregistered-online-investment-schemes/'


def check_copy(copy: str, channel: str, licenses: list[str]) -> dict:
    findings = []
    bank_licensed = any(value.lower().replace(' ', '_') in {
        'commercial_bank','microfinance_bank','mfb','payment_service_bank','psb','banking_license'
    } for value in licenses)
    sentences = list(re.finditer(r'[^.!?\n]+(?:[.!?]+|$)', copy))
    for sentence in sentences:
        value = sentence.group()
        rules = []
        if re.search(r'\b(?:guaranteed?\s+(?:(?:\d+(?:\.\d+)?\s*%|daily|monthly|annual|investment|high|fixed)\s*)*(?:returns?|profits?|yields?)|risk[ -]?free\s+(?:investment|returns?|profits?)|double\s+your\s+money)\b',value,re.I):
            rules.append(('investment_promises','high','Return and risk claims need substantiation and registration checks.',
                SEC_SOURCE,'SEC public notice on unregistered investment schemes, May 2026',
                'Investment outcomes vary and capital may be at risk. Review the product terms, fees and risk disclosures.'))
        if not bank_licensed and re.search(r'\b(?:we are (?:a|your) bank|(?:our|open a|open your) (?:bank|savings|deposit) account|bank with us|deposit[- ]taking)\b',value,re.I):
            rules.append(('banking_scope','high','Banking claims require evidence that the provider and product have the stated authorization.',
                CBN_SOURCE,'CBN Consumer Protection Regulations, 4.2.1',
                'Explore our financial services. Confirm the licensed provider, product scope and terms before opening an account.'))
        if re.search(r'\b(?:send|transfer|remit)\b.*\b(?:anywhere|every country|all countries|worldwide|without limits|no limits|no verification|no kyc)\b',value,re.I):
            rules.append(('remittance_scope','medium','Verify supported corridors, authorization, limits and identity checks before making this claim.',
                CBN_SOURCE,'CBN Consumer Protection Regulations, 4.2.1–4.2.2',
                'Transfers are available on supported corridors, subject to eligibility checks, limits, fees and processing times.'))
        if re.search(r'\b(?:zero fees|no fees|free forever|instant (?:settlement|transfers?))\b',value,re.I):
            rules.append(('cost_or_speed_claim','medium','Verify costs and timing conditions and disclose applicable limitations.',
                CBN_SOURCE,'CBN Consumer Protection Regulations, 4.2.1 and 4.2.4',
                'Check the applicable fees and estimated processing time before confirming your transaction.'))
        for code,severity,reason,url,reference,alternative in rules:
            findings.append({'rule_id': code,'severity': severity,'start': sentence.start(),'end': sentence.end(),
                'excerpt': value,'reason': reason,'source_url': url,'reference': reference,
                'suggested_alternative': alternative,'requires_human_review': True})
    if channel in {'sms','email'} and not re.search(r'\b(?:unsubscribe|opt[ -]?out|stop)\b',copy,re.I):
        findings.append({'rule_id':'opt_out','severity':'medium','start':0,'end':len(copy),'excerpt':copy,
            'reason':'If this is unsolicited promotional messaging, include a free opt-out mechanism.',
            'source_url':CBN_SOURCE,'reference':'CBN Consumer Protection Regulations, 4.2.8',
            'suggested_alternative':'Add a working opt-out instruction that is free to the recipient.',
            'requires_human_review':True})
    return {'findings': findings,'rules_version': RULES_VERSION,
        'status':'review_required' if findings else 'no_flags_in_checked_rules',
        'scope':'Automated screening of selected advertising claims; absence of flags is not regulatory approval.',
        'license_context':licenses,'approved':False}
