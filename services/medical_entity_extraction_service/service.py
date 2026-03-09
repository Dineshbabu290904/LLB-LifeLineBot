import re
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8010"
    llm_model: str = "llama3.2"
    llm_timeout: float = 30.0
    use_llm_augmentation: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


class ExtractedEntity(BaseModel):
    entity_type: str
    name: str
    normalized_name: str
    confidence: float
    source_text: str


# ---------------------------------------------------------------------------
# Regex pattern library
# ---------------------------------------------------------------------------

SYMPTOM_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"\b(headache|head\s+ache|cephalgia)\b", "normalized": "headache"},
    {"pattern": r"\b(migraine)\b", "normalized": "migraine"},
    {"pattern": r"\b(fever|pyrexia|febrile)\b", "normalized": "fever"},
    {"pattern": r"\b(cough|coughing)\b", "normalized": "cough"},
    {"pattern": r"\b(chest\s+pain|chest\s+tightness|chest\s+pressure|chest\s+discomfort)\b", "normalized": "chest pain"},
    {"pattern": r"\b(shortness\s+of\s+breath|dyspnea|dyspnoea|breathlessness|difficulty\s+breathing)\b", "normalized": "dyspnea"},
    {"pattern": r"\b(nausea|nauseous)\b", "normalized": "nausea"},
    {"pattern": r"\b(vomiting|vomit|emesis|throwing\s+up)\b", "normalized": "vomiting"},
    {"pattern": r"\b(diarrhea|diarrhoea|loose\s+stool)\b", "normalized": "diarrhea"},
    {"pattern": r"\b(constipation|constipated)\b", "normalized": "constipation"},
    {"pattern": r"\b(fatigue|tiredness|exhaustion|lethargy|weakness)\b", "normalized": "fatigue"},
    {"pattern": r"\b(dizziness|dizzy|vertigo|lightheaded)\b", "normalized": "dizziness"},
    {"pattern": r"\b(palpitations?|heart\s+racing|rapid\s+heart)\b", "normalized": "palpitations"},
    {"pattern": r"\b(abdominal\s+pain|stomach\s+pain|belly\s+pain|stomach\s+ache|stomachache)\b", "normalized": "abdominal pain"},
    {"pattern": r"\b(back\s+pain|backache|lumbar\s+pain)\b", "normalized": "back pain"},
    {"pattern": r"\b(joint\s+pain|arthralgia|joint\s+ache)\b", "normalized": "joint pain"},
    {"pattern": r"\b(muscle\s+pain|myalgia|muscle\s+ache)\b", "normalized": "myalgia"},
    {"pattern": r"\b(sore\s+throat|pharyngitis|throat\s+pain)\b", "normalized": "sore throat"},
    {"pattern": r"\b(runny\s+nose|rhinorrhea|nasal\s+discharge)\b", "normalized": "rhinorrhea"},
    {"pattern": r"\b(rash|skin\s+rash|urticaria|hives)\b", "normalized": "rash"},
    {"pattern": r"\b(swelling|edema|oedema|swollen)\b", "normalized": "edema"},
    {"pattern": r"\b(blurred\s+vision|vision\s+changes|visual\s+disturbance)\b", "normalized": "visual disturbance"},
    {"pattern": r"\b(numbness|tingling|paresthesia)\b", "normalized": "paresthesia"},
    {"pattern": r"\b(confusion|disorientation|altered\s+consciousness)\b", "normalized": "confusion"},
    {"pattern": r"\b(seizure|convulsion|epileptic)\b", "normalized": "seizure"},
    {"pattern": r"\b(syncope|fainting|passed\s+out|loss\s+of\s+consciousness)\b", "normalized": "syncope"},
    {"pattern": r"\b(insomnia|sleeplessness|can'?t\s+sleep)\b", "normalized": "insomnia"},
    {"pattern": r"\b(anxiety|anxious|panic\s+attack)\b", "normalized": "anxiety"},
    {"pattern": r"\b(depression|depressed|low\s+mood)\b", "normalized": "depression"},
    {"pattern": r"\b(itching|pruritus|itchy)\b", "normalized": "pruritus"},
    {"pattern": r"\b(loss\s+of\s+appetite|anorexia|not\s+eating)\b", "normalized": "anorexia"},
    {"pattern": r"\b(weight\s+loss|losing\s+weight)\b", "normalized": "weight loss"},
    {"pattern": r"\b(weight\s+gain|gaining\s+weight)\b", "normalized": "weight gain"},
    {"pattern": r"\b(night\s+sweats|sweating\s+at\s+night)\b", "normalized": "night sweats"},
    {"pattern": r"\b(hemoptysis|coughing\s+up\s+blood|blood\s+in\s+sputum)\b", "normalized": "hemoptysis"},
    {"pattern": r"\b(hematuria|blood\s+in\s+urine)\b", "normalized": "hematuria"},
    {"pattern": r"\b(hematochezia|blood\s+in\s+stool|rectal\s+bleeding)\b", "normalized": "rectal bleeding"},
    {"pattern": r"\b(jaundice|yellowing\s+of\s+skin|yellow\s+skin|icterus)\b", "normalized": "jaundice"},
    {"pattern": r"\b(pallor|pale\s+skin|paleness)\b", "normalized": "pallor"},
    {"pattern": r"\b(polyuria|frequent\s+urination|urinary\s+frequency)\b", "normalized": "polyuria"},
    {"pattern": r"\b(polydipsia|excessive\s+thirst|increased\s+thirst)\b", "normalized": "polydipsia"},
    {"pattern": r"\b(dysuria|painful\s+urination|burning\s+urination)\b", "normalized": "dysuria"},
    {"pattern": r"\b(tinnitus|ringing\s+in\s+ears|ear\s+ringing)\b", "normalized": "tinnitus"},
    {"pattern": r"\b(hearing\s+loss|hard\s+of\s+hearing|deafness)\b", "normalized": "hearing loss"},
]

MEDICATION_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"\b(aspirin|acetylsalicylic\s+acid|asa)\b", "normalized": "aspirin"},
    {"pattern": r"\b(ibuprofen|advil|motrin|nurofen)\b", "normalized": "ibuprofen"},
    {"pattern": r"\b(acetaminophen|paracetamol|tylenol|panadol)\b", "normalized": "acetaminophen"},
    {"pattern": r"\b(naproxen|aleve|naprosyn)\b", "normalized": "naproxen"},
    {"pattern": r"\b(metformin|glucophage)\b", "normalized": "metformin"},
    {"pattern": r"\b(lisinopril|zestril|prinivil)\b", "normalized": "lisinopril"},
    {"pattern": r"\b(atorvastatin|lipitor)\b", "normalized": "atorvastatin"},
    {"pattern": r"\b(simvastatin|zocor)\b", "normalized": "simvastatin"},
    {"pattern": r"\b(amlodipine|norvasc)\b", "normalized": "amlodipine"},
    {"pattern": r"\b(metoprolol|lopressor|toprol)\b", "normalized": "metoprolol"},
    {"pattern": r"\b(omeprazole|prilosec|losec)\b", "normalized": "omeprazole"},
    {"pattern": r"\b(pantoprazole|protonix)\b", "normalized": "pantoprazole"},
    {"pattern": r"\b(amoxicillin|amoxil)\b", "normalized": "amoxicillin"},
    {"pattern": r"\b(azithromycin|zithromax|z-pak)\b", "normalized": "azithromycin"},
    {"pattern": r"\b(ciprofloxacin|cipro)\b", "normalized": "ciprofloxacin"},
    {"pattern": r"\b(doxycycline|vibramycin)\b", "normalized": "doxycycline"},
    {"pattern": r"\b(prednisone|deltasone)\b", "normalized": "prednisone"},
    {"pattern": r"\b(prednisolone)\b", "normalized": "prednisolone"},
    {"pattern": r"\b(albuterol|salbutamol|ventolin|proair)\b", "normalized": "albuterol"},
    {"pattern": r"\b(sertraline|zoloft)\b", "normalized": "sertraline"},
    {"pattern": r"\b(fluoxetine|prozac)\b", "normalized": "fluoxetine"},
    {"pattern": r"\b(escitalopram|lexapro)\b", "normalized": "escitalopram"},
    {"pattern": r"\b(warfarin|coumadin)\b", "normalized": "warfarin"},
    {"pattern": r"\b(apixaban|eliquis)\b", "normalized": "apixaban"},
    {"pattern": r"\b(rivaroxaban|xarelto)\b", "normalized": "rivaroxaban"},
    {"pattern": r"\b(insulin)\b", "normalized": "insulin"},
    {"pattern": r"\b(levothyroxine|synthroid)\b", "normalized": "levothyroxine"},
    {"pattern": r"\b(gabapentin|neurontin)\b", "normalized": "gabapentin"},
    {"pattern": r"\b(hydrochlorothiazide|hctz)\b", "normalized": "hydrochlorothiazide"},
    {"pattern": r"\b(losartan|cozaar)\b", "normalized": "losartan"},
    {"pattern": r"\b(furosemide|lasix)\b", "normalized": "furosemide"},
    {"pattern": r"\b(clopidogrel|plavix)\b", "normalized": "clopidogrel"},
    {"pattern": r"\b(morphine)\b", "normalized": "morphine"},
    {"pattern": r"\b(oxycodone|percocet|oxycontin)\b", "normalized": "oxycodone"},
    {"pattern": r"\b(tramadol|ultram)\b", "normalized": "tramadol"},
    {"pattern": r"\b(codeine)\b", "normalized": "codeine"},
    {"pattern": r"\b(cetirizine|zyrtec)\b", "normalized": "cetirizine"},
    {"pattern": r"\b(loratadine|claritin)\b", "normalized": "loratadine"},
    {"pattern": r"\b(diphenhydramine|benadryl)\b", "normalized": "diphenhydramine"},
    {"pattern": r"\b(diazepam|valium)\b", "normalized": "diazepam"},
    {"pattern": r"\b(lorazepam|ativan)\b", "normalized": "lorazepam"},
    {"pattern": r"\b(alprazolam|xanax)\b", "normalized": "alprazolam"},
]

CONDITION_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"\b(diabetes|diabetic|type\s*[12]\s+diabetes|t2dm|t1dm)\b", "normalized": "diabetes mellitus"},
    {"pattern": r"\b(hypertension|high\s+blood\s+pressure|hbp)\b", "normalized": "hypertension"},
    {"pattern": r"\b(hypotension|low\s+blood\s+pressure)\b", "normalized": "hypotension"},
    {"pattern": r"\b(asthma|asthmatic)\b", "normalized": "asthma"},
    {"pattern": r"\b(copd|chronic\s+obstructive\s+pulmonary\s+disease|emphysema|chronic\s+bronchitis)\b", "normalized": "COPD"},
    {"pattern": r"\b(pneumonia|pneumonitis)\b", "normalized": "pneumonia"},
    {"pattern": r"\b(heart\s+failure|congestive\s+heart\s+failure|chf|cardiac\s+failure)\b", "normalized": "heart failure"},
    {"pattern": r"\b(myocardial\s+infarction|heart\s+attack|mi)\b", "normalized": "myocardial infarction"},
    {"pattern": r"\b(stroke|cerebrovascular\s+accident|cva)\b", "normalized": "stroke"},
    {"pattern": r"\b(atrial\s+fibrillation|a-?fib|afib)\b", "normalized": "atrial fibrillation"},
    {"pattern": r"\b(cancer|carcinoma|malignancy|tumor|tumour|neoplasm|lymphoma|leukemia|leukaemia)\b", "normalized": "cancer"},
    {"pattern": r"\b(depression|major\s+depressive\s+disorder|mdd)\b", "normalized": "depression"},
    {"pattern": r"\b(anxiety\s+disorder|generalized\s+anxiety|gad|panic\s+disorder)\b", "normalized": "anxiety disorder"},
    {"pattern": r"\b(hypothyroidism|underactive\s+thyroid)\b", "normalized": "hypothyroidism"},
    {"pattern": r"\b(hyperthyroidism|overactive\s+thyroid|graves\s+disease)\b", "normalized": "hyperthyroidism"},
    {"pattern": r"\b(chronic\s+kidney\s+disease|ckd|renal\s+failure|kidney\s+failure)\b", "normalized": "chronic kidney disease"},
    {"pattern": r"\b(urinary\s+tract\s+infection|uti|cystitis)\b", "normalized": "urinary tract infection"},
    {"pattern": r"\b(gerd|gastroesophageal\s+reflux|acid\s+reflux|heartburn)\b", "normalized": "GERD"},
    {"pattern": r"\b(irritable\s+bowel|ibs)\b", "normalized": "irritable bowel syndrome"},
    {"pattern": r"\b(crohn'?s|crohn\s+disease|inflammatory\s+bowel|ulcerative\s+colitis)\b", "normalized": "inflammatory bowel disease"},
    {"pattern": r"\b(rheumatoid\s+arthritis|ra)\b", "normalized": "rheumatoid arthritis"},
    {"pattern": r"\b(osteoarthritis|degenerative\s+joint)\b", "normalized": "osteoarthritis"},
    {"pattern": r"\b(osteoporosis)\b", "normalized": "osteoporosis"},
    {"pattern": r"\b(epilepsy|epileptic)\b", "normalized": "epilepsy"},
    {"pattern": r"\b(parkinson'?s|parkinson\s+disease)\b", "normalized": "Parkinson's disease"},
    {"pattern": r"\b(alzheimer'?s|alzheimer\s+disease|dementia)\b", "normalized": "dementia"},
    {"pattern": r"\b(multiple\s+sclerosis|ms)\b", "normalized": "multiple sclerosis"},
    {"pattern": r"\b(hiv|human\s+immunodeficiency\s+virus|aids)\b", "normalized": "HIV/AIDS"},
    {"pattern": r"\b(tuberculosis|tb)\b", "normalized": "tuberculosis"},
    {"pattern": r"\b(sepsis|septicemia|blood\s+poisoning)\b", "normalized": "sepsis"},
    {"pattern": r"\b(anemia|anaemia)\b", "normalized": "anemia"},
    {"pattern": r"\b(deep\s+vein\s+thrombosis|dvt|blood\s+clot)\b", "normalized": "deep vein thrombosis"},
    {"pattern": r"\b(pulmonary\s+embolism|pe)\b", "normalized": "pulmonary embolism"},
    {"pattern": r"\b(appendicitis)\b", "normalized": "appendicitis"},
    {"pattern": r"\b(cholecystitis|gallbladder\s+disease|gallstones?)\b", "normalized": "gallbladder disease"},
    {"pattern": r"\b(pancreatitis)\b", "normalized": "pancreatitis"},
    {"pattern": r"\b(hepatitis)\b", "normalized": "hepatitis"},
    {"pattern": r"\b(cirrhosis|liver\s+disease|liver\s+failure)\b", "normalized": "liver disease"},
    {"pattern": r"\b(psoriasis)\b", "normalized": "psoriasis"},
    {"pattern": r"\b(eczema|atopic\s+dermatitis)\b", "normalized": "eczema"},
    {"pattern": r"\b(lupus|systemic\s+lupus|sle)\b", "normalized": "systemic lupus erythematosus"},
]

PROCEDURE_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"\b(mri|magnetic\s+resonance\s+imaging)\b", "normalized": "MRI"},
    {"pattern": r"\b(ct\s+scan|computed\s+tomography|cat\s+scan)\b", "normalized": "CT scan"},
    {"pattern": r"\b(x-?ray|radiograph)\b", "normalized": "X-ray"},
    {"pattern": r"\b(ultrasound|sonogram|sonography)\b", "normalized": "ultrasound"},
    {"pattern": r"\b(ecg|ekg|electrocardiogram)\b", "normalized": "ECG"},
    {"pattern": r"\b(echocardiogram|echo)\b", "normalized": "echocardiogram"},
    {"pattern": r"\b(biopsy)\b", "normalized": "biopsy"},
    {"pattern": r"\b(colonoscopy)\b", "normalized": "colonoscopy"},
    {"pattern": r"\b(endoscopy|gastroscopy)\b", "normalized": "endoscopy"},
    {"pattern": r"\b(bronchoscopy)\b", "normalized": "bronchoscopy"},
    {"pattern": r"\b(angiography|angiogram)\b", "normalized": "angiography"},
    {"pattern": r"\b(angioplasty|stent\s+placement)\b", "normalized": "angioplasty"},
    {"pattern": r"\b(dialysis|hemodialysis)\b", "normalized": "dialysis"},
    {"pattern": r"\b(chemotherapy|chemo)\b", "normalized": "chemotherapy"},
    {"pattern": r"\b(radiation\s+therapy|radiotherapy)\b", "normalized": "radiation therapy"},
    {"pattern": r"\b(surgery|surgical\s+procedure|operation)\b", "normalized": "surgery"},
    {"pattern": r"\b(appendectomy)\b", "normalized": "appendectomy"},
    {"pattern": r"\b(cholecystectomy)\b", "normalized": "cholecystectomy"},
    {"pattern": r"\b(blood\s+test|blood\s+work|lab\s+test|laboratory\s+test)\b", "normalized": "blood test"},
    {"pattern": r"\b(lumbar\s+puncture|spinal\s+tap)\b", "normalized": "lumbar puncture"},
    {"pattern": r"\b(pacemaker\s+implant|pacemaker\s+insertion)\b", "normalized": "pacemaker implantation"},
    {"pattern": r"\b(vaccination|immunization|vaccine)\b", "normalized": "vaccination"},
    {"pattern": r"\b(intubation|mechanical\s+ventilation)\b", "normalized": "mechanical ventilation"},
    {"pattern": r"\b(cpr|cardiopulmonary\s+resuscitation)\b", "normalized": "CPR"},
    {"pattern": r"\b(defibrillation)\b", "normalized": "defibrillation"},
]

ANATOMY_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"\b(heart|cardiac|myocardium)\b", "normalized": "heart"},
    {"pattern": r"\b(lung|pulmonary|respiratory)\b", "normalized": "lung"},
    {"pattern": r"\b(liver|hepatic)\b", "normalized": "liver"},
    {"pattern": r"\b(kidney|renal|nephro)\b", "normalized": "kidney"},
    {"pattern": r"\b(brain|cerebral|neural|neurological)\b", "normalized": "brain"},
    {"pattern": r"\b(stomach|gastric|gastro)\b", "normalized": "stomach"},
    {"pattern": r"\b(intestine|bowel|colon|rectal)\b", "normalized": "intestine"},
    {"pattern": r"\b(pancreas|pancreatic)\b", "normalized": "pancreas"},
    {"pattern": r"\b(thyroid)\b", "normalized": "thyroid"},
    {"pattern": r"\b(spinal\s+cord|spine|vertebral)\b", "normalized": "spine"},
    {"pattern": r"\b(joint|articular)\b", "normalized": "joint"},
    {"pattern": r"\b(bone|skeletal|osseous)\b", "normalized": "bone"},
    {"pattern": r"\b(muscle|muscular)\b", "normalized": "muscle"},
    {"pattern": r"\b(skin|dermal|cutaneous)\b", "normalized": "skin"},
    {"pattern": r"\b(eye|ocular|optic)\b", "normalized": "eye"},
    {"pattern": r"\b(ear|auditory|otic)\b", "normalized": "ear"},
    {"pattern": r"\b(nose|nasal)\b", "normalized": "nose"},
    {"pattern": r"\b(throat|pharynx|larynx)\b", "normalized": "throat"},
    {"pattern": r"\b(blood\s+vessel|artery|vein|vascular)\b", "normalized": "blood vessel"},
    {"pattern": r"\b(lymph\s+node|lymphatic)\b", "normalized": "lymph node"},
    {"pattern": r"\b(bladder|urinary\s+bladder)\b", "normalized": "bladder"},
    {"pattern": r"\b(prostate)\b", "normalized": "prostate"},
    {"pattern": r"\b(uterus|uterine|womb)\b", "normalized": "uterus"},
    {"pattern": r"\b(ovary|ovarian)\b", "normalized": "ovary"},
    {"pattern": r"\b(breast|mammary)\b", "normalized": "breast"},
    {"pattern": r"\b(gallbladder|biliary)\b", "normalized": "gallbladder"},
    {"pattern": r"\b(appendix|appendiceal)\b", "normalized": "appendix"},
    {"pattern": r"\b(aorta|aortic)\b", "normalized": "aorta"},
    {"pattern": r"\b(trachea|windpipe)\b", "normalized": "trachea"},
    {"pattern": r"\b(esophagus|oesophagus|esophageal)\b", "normalized": "esophagus"},
]

MEASUREMENT_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"\b(blood\s+pressure|bp)\s*:?\s*(\d{2,3}\s*/\s*\d{2,3})", "normalized": "blood pressure"},
    {"pattern": r"\b(temperature|temp)\s*:?\s*(\d{2,3}(?:\.\d)?)\s*(?:°?[fc])", "normalized": "body temperature"},
    {"pattern": r"\b(heart\s+rate|pulse|bpm)\s*:?\s*(\d{2,3})", "normalized": "heart rate"},
    {"pattern": r"\b(oxygen\s+saturation|spo2|o2\s+sat)\s*:?\s*(\d{2,3})%?", "normalized": "oxygen saturation"},
    {"pattern": r"\b(blood\s+sugar|blood\s+glucose|glucose)\s*:?\s*(\d{2,3}(?:\.\d)?)", "normalized": "blood glucose"},
    {"pattern": r"\b(bmi|body\s+mass\s+index)\s*:?\s*(\d{1,2}(?:\.\d)?)", "normalized": "BMI"},
    {"pattern": r"\b(weight)\s*:?\s*(\d{2,3}(?:\.\d)?)\s*(?:kg|lbs?|pounds?)", "normalized": "body weight"},
    {"pattern": r"\b(height)\s*:?\s*(\d{1,3}(?:\.\d)?)\s*(?:cm|m|ft|feet|inches?)", "normalized": "height"},
    {"pattern": r"\b(cholesterol)\s*:?\s*(\d{2,3}(?:\.\d)?)", "normalized": "cholesterol level"},
    {"pattern": r"\b(creatinine)\s*:?\s*(\d+(?:\.\d+)?)", "normalized": "creatinine level"},
    {"pattern": r"\b(hemoglobin|hgb|hb)\s*:?\s*(\d+(?:\.\d+)?)", "normalized": "hemoglobin level"},
    {"pattern": r"\b(white\s+blood\s+cell|wbc)\s*count\s*:?\s*(\d+(?:\.\d+)?)", "normalized": "WBC count"},
    {"pattern": r"\b(platelet)\s*count\s*:?\s*(\d+(?:\.\d+)?)", "normalized": "platelet count"},
    {"pattern": r"\b(respiratory\s+rate|rr|breathing\s+rate)\s*:?\s*(\d{1,2})", "normalized": "respiratory rate"},
    {"pattern": r"\b(pain\s+scale|pain\s+level|pain\s+score)\s*:?\s*(\d{1,2}(?:/10)?)", "normalized": "pain score"},
]

ENTITY_CONFIG = {
    "symptom": SYMPTOM_PATTERNS,
    "medication": MEDICATION_PATTERNS,
    "condition": CONDITION_PATTERNS,
    "procedure": PROCEDURE_PATTERNS,
    "anatomy": ANATOMY_PATTERNS,
    "measurement": MEASUREMENT_PATTERNS,
}


def extract_entities_regex(text: str, entity_types: Optional[List[str]] = None) -> List[ExtractedEntity]:
    """Extract medical entities using regex pattern matching."""
    if entity_types is None:
        entity_types = list(ENTITY_CONFIG.keys())

    results: List[ExtractedEntity] = []
    seen: set = set()
    text_lower = text.lower()

    for etype in entity_types:
        if etype not in ENTITY_CONFIG:
            continue
        patterns = ENTITY_CONFIG[etype]
        for pat_def in patterns:
            compiled = re.compile(pat_def["pattern"], re.IGNORECASE)
            for match in compiled.finditer(text_lower):
                matched_text = match.group(0).strip()
                normalized = pat_def["normalized"]
                key = (etype, normalized)
                if key in seen:
                    continue
                seen.add(key)
                results.append(ExtractedEntity(
                    entity_type=etype,
                    name=matched_text,
                    normalized_name=normalized,
                    confidence=0.85,
                    source_text=_get_context(text, match.start(), match.end()),
                ))

    return results


def _get_context(text: str, start: int, end: int, window: int = 40) -> str:
    """Return surrounding context for a match."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    snippet = text[ctx_start:ctx_end]
    if ctx_start > 0:
        snippet = "..." + snippet
    if ctx_end < len(text):
        snippet = snippet + "..."
    return snippet


async def extract_entities_llm(text: str, regex_entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
    """Use LLM to augment regex extraction and find missed entities."""
    known = {e.normalized_name for e in regex_entities}

    existing_summary = ", ".join(
        f"{e.entity_type}:{e.normalized_name}" for e in regex_entities[:15]
    ) or "none"

    prompt = (
        "You are a medical NER system. Extract medical entities from the text below.\n"
        "Entity types: symptom, medication, condition, procedure, anatomy, measurement\n"
        f"Already found: {existing_summary}\n"
        "Return ONLY new entities not already listed, one per line in format:\n"
        "entity_type|name|normalized_name|confidence(0-1)\n"
        "If no new entities, return NONE.\n\n"
        f"Text: {text[:1000]}"
    )

    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            resp = await client.post(
                f"{settings.ollama_router_url}/api/generate",
                json={"model": settings.llm_model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")
    except Exception:
        return []

    llm_entities: List[ExtractedEntity] = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or line.upper() == "NONE":
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        etype, name, normalized = parts[0], parts[1], parts[2]
        try:
            confidence = float(parts[3]) if len(parts) > 3 else 0.7
        except ValueError:
            confidence = 0.7
        if etype not in ENTITY_CONFIG:
            continue
        if normalized.lower() in known:
            continue
        llm_entities.append(ExtractedEntity(
            entity_type=etype,
            name=name,
            normalized_name=normalized,
            confidence=min(confidence, 0.8),  # cap LLM confidence
            source_text=text[:100],
        ))

    return llm_entities


async def extract_entities(
    text: str,
    entity_types: Optional[List[str]] = None,
    use_llm: bool = True,
) -> List[ExtractedEntity]:
    """Full extraction pipeline: regex + optional LLM augmentation."""
    regex_results = extract_entities_regex(text, entity_types)

    if use_llm and settings.use_llm_augmentation:
        llm_results = await extract_entities_llm(text, regex_results)
        regex_results.extend(llm_results)

    # Sort: higher confidence first, then by entity type
    regex_results.sort(key=lambda e: (-e.confidence, e.entity_type, e.normalized_name))
    return regex_results
