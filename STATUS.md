# Evaluation Pipeline Status

**Last Updated:** 2026-05-01 (batch 28 — third PheKB-aligned batch; first PGx phenotypes)

## Phenotype Progress Tracker

108 phenotypes downloaded from PheKB. 93 basic test cases auto-generated. The table below tracks the **deep evaluation pipeline** for each phenotype (algorithm analysis, multi-path test cases, Synthea data, LLM evaluation). 100 phenotypes deeply done.

### Legend
- **Algorithm Analyzed**: PheKB algorithm PDF read, paths identified, codes verified via UMLS
- **Test Cases (Multi-Path)**: Per-path test cases + comprehensive provider query created
- **Synthea Module**: Multi-path module with path-specific patient generation
- **Data Generated**: Synthea patients generated and loaded into HAPI FHIR
- **T1/T2 columns**: F1 score on diagnosis (-dx) test case. T1 = Closed Book, T2 = Agentic (with tools)

### Evaluation Results

| Phenotype | Algorithm Analyzed | Test Cases | Synthea Module | Data Generated | T1 qwen2.5:7b | T2 qwen2.5:7b |
|-----------|:--:|:--:|:--:|:--:|:--:|:--:|
| **Type 2 Diabetes** | Yes | 6 cases revalidated 2026-04-29 (dx=44 with 3 SNOMED variants, meds=65, labs=74, comp=74, path4=74) | Yes (multi-path + 3 SNOMED variants added 2026-04-29) | 100+ pos / 25 ctrl | **0.00** | **0.00** |
| **Abdominal Aortic Aneurysm** | Yes | 3 cases per-path created 2026-04-29 (dx=10 with 2 SNOMED variants, procedures=3, comp=10) — replaced orphan auto-gen test | Yes (multi-path + 2 SNOMED variants) | 22 pos / 22 ctrl | **0.00** | **0.00** |
| **ACE Inhibitor Cough** | Yes | 3 cases revalidated 2026-04-29 (dx=10 with 2 SNOMED, meds=14, comp=14) | Yes (multi-path, already had 2 SNOMED + 5 ACE-Is) | 22 pos / 22 ctrl | **0.00** | **1.00** |
| **Acute Kidney Injury** | Yes | 3 cases per-path created 2026-04-29 (dx=10, labs [Cr≥1.5]=14, comp=14) — replaced orphan auto-gen test | Yes (multi-path) | 22 pos / 18 ctrl | **0.00** | **1.00** |
| **ADHD** | Yes | 3 cases revalidated 2026-04-29 (dx=53 with 3 SNOMED variants, meds=73, comp=73) | Yes (multi-path + 3 SNOMED variants added 2026-04-29) | 80+ pos / 22 ctrl | **0.00** | **1.00** |
| **Anxiety** | Yes | 3 cases revalidated 2026-04-29 (dx=10 with 3 SNOMED variants, meds=15, comp=15) | Yes (already had 3 SNOMED variants pre-refresh) | 22 pos / 15 ctrl | **0.00** | **0.00** |
| **Appendicitis** | Yes | 3 cases revalidated 2026-04-29 (dx=55 with 2 SNOMED variants, procedures=4, comp=56) | Yes (multi-path + 2 SNOMED variants added 2026-04-29) | 80+ pos / 22 ctrl | **0.00** | **1.00** |
| **Asthma** | Yes | 3 cases revalidated 2026-04-29 (dx=54 with 4 SNOMED variants, meds=76, comp=76) | Yes (multi-path + 4 SNOMED variants added 2026-04-29 — most variation in old phenotypes) | 80+ pos / 22 ctrl | **0.00** | **1.00** |
| **Atopic Dermatitis** | Yes | 3 cases revalidated 2026-04-29 (dx=61 with 2 SNOMED variants, meds=79, comp=79) | Yes (multi-path + 2 SNOMED variants added 2026-04-29) | 80+ pos / 14 ctrl | **0.00** | **0.00** |
| **Atrial Fibrillation** | Yes | 3 cases revalidated 2026-04-29 (dx=25 with 3 SNOMED variants paroxysmal/persistent/chronic, meds=37, comp=37) | Yes (multi-path + 3 SNOMED variants added 2026-04-29) | 80+ pos / 18 ctrl | **0.00** | **1.00** |
| **Autism** | Yes | 3 cases revalidated 2026-04-29 (dx=50 with 3 SNOMED variants PDD/Autistic/Asperger's, meds=76, comp=76) | Yes (multi-path + 3 SNOMED variants added 2026-04-29) | 80+ pos / 22 ctrl | **0.00** | **0.00** |
| **Sickle Cell Disease** | Yes | 4 cases (dx, meds, meds-only, comprehensive) | Yes (multi-path + code variation) | 30 pos / ctrl | - | - |
| **Hypothyroidism** | Yes | 6 cases validated (dx=11, meds=16, labs=12, meds-only=5, labs-only=2, comp=18) | Yes (4-path + 5 SNOMED + 4 RxNorm SCD variants) | 32 pos / 27 ctrl | - | - |
| **Dementia** | Yes | 4 cases validated (dx=23, meds=38, meds-only=22, comp=45) | Yes (3-path + 5 SNOMED subtypes + 5 RxNorm SCD variants) | 140 pos / 79 ctrl | - | - |
| **Depression** | Yes | 4 cases validated (dx=12, meds=20, meds-only=13 [65% Path C], comp=25) | Yes (3-path heavy Path C + 5 SNOMED + 6 RxNorm SCD variants) | 35 pos / 27 ctrl | - | - |
| **Heart Failure** | Yes | 5 cases validated (dx=7, meds=12, labs [EF<50]=3, meds-only=5, comp=13) | Yes (4-path + 5 SNOMED HFrEF/HFpEF + 5 RxNorm GDMT) | 50 pos / 30 ctrl | - | - |
| **Rheumatoid Arthritis** | Yes | 5 cases validated (dx=19, meds=29, labs [RF>14]=3, meds-only=10, comp=30) | Yes (4-path + 5 SNOMED + 5 DMARD/biologic ingredients) | 50 pos / 30 ctrl | - | - |
| **Chronic Kidney Disease** | Yes | 5 cases validated (dx=6, labs [eGFR<60]=14, labs-only=8, albuminuria=4, comp=15) | Yes (4-path + 5 SNOMED CKD stages, eGFR + UACR labs) | 50 pos / 30 ctrl | - | - |
| **Breast Cancer** | Yes | 4 cases validated (dx=21, meds=15, meds-only=2, comp=23) | Yes (3-path + 5 SNOMED histologies + 5 endocrine/HER2 therapies) | 50 pos / 30 ctrl | - | - |
| **GERD** | Yes | 4 cases validated (dx=16, meds=31, meds-only=22 [Path C 58%], comp=38) | Yes (3-path heavy Path C 50% + 3 SNOMED + 5 PPI ingredients) | 50 pos / 30 ctrl | - | - |
| **Multiple Sclerosis** | Yes | 4 cases validated (dx=39, meds=31, meds-only=1, comp=40) | Yes (3-path + 5 SNOMED MS courses + 5 DMT ingredients) | 50 pos / 30 ctrl | - | - |
| **Hypertension** | Yes | 5 cases validated (dx=15, meds=27, vitals [SBP>140]=5, meds-only=12, comp=28) | Yes (4-path + 5 SNOMED HTN subtypes + 5 antihypertensive classes) | 50 pos / 30 ctrl | - | - |
| **Familial Hypercholesterolemia** | Yes | 5 cases validated (dx=17, meds=23, labs [LDL≥190]=4, labs-only=2, comp=25) | Yes (4-path + 5 SNOMED FH genetic variants + 5 statins) | 50 pos / 30 ctrl | - | - |
| **Hepatitis C** | Yes | 5 cases validated (dx=21, meds=20, labs [HCV Ab]=10, meds-only=4, comp=27) | Yes (4-path + 3 SNOMED acuity codes + 4 DAAs) | 50 pos / 30 ctrl | - | - |
| **Type 1 Diabetes** | Yes | 4 cases validated (dx=38, meds=42, labs [HbA1c≥6.5]=7, comp=42) | Yes (3-path + 5 SNOMED T1D variants + 5 insulin codes) | 50 pos / 30 ctrl | - | - |
| **HIV** | Yes | 4 cases validated (dx=31, meds=31, labs [CD4<200]=7, comp=32) | Yes (4-path + 4 SNOMED stages + 5 ART combination tablets) | 50 pos / 30 ctrl | - | - |
| **Coronary Heart Disease** | Yes | 4 cases validated (dx=13, meds=38, **procedures=7 FIRST**, comp=40) | Yes (4-path + 5 SNOMED + 5 meds + 4 PROCEDURES) | 50 pos / 30 ctrl | - | - |
| **Venous Thromboembolism** | Yes | 5 cases validated (dx=29, meds=37, labs [D-dimer>0.5]=7, meds-only=8, comp=37) | Yes (4-path + 5 SNOMED DVT/PE + 5 anticoagulants) | 72 pos / 32 ctrl | - | - |
| **Sleep Apnea** | Yes | 3 cases validated (dx=36, **procedures [polysomnography]=4 SECOND**, comp=38) | Yes (3-path + 5 SNOMED OSA/CSA subtypes + Procedure) | 82 pos / 32 ctrl | - | - |
| **Crohn's Disease** | Yes | 4 cases validated (dx=28, meds=53, labs [calprotectin>250]=3, comp=55) | Yes (4-path + 5 SNOMED locations + 5 IBD meds) | 72 pos / 32 ctrl | - | - |
| **Colorectal Cancer** | Yes | 5 cases validated (dx=22, meds=22, labs [CEA>5]=9, **procedures [colonoscopy]=4 THIRD**, comp=27 first 4-resource union) | Yes (4-path + 5 SNOMED anatomic + 5 chemo + colonoscopy + CEA) | 72 pos / 32 ctrl | - | - |
| **Migraine** | Yes | 3 cases validated (dx=43, meds [triptans]=49, comp=57) | Yes (3-path + 5 SNOMED subtypes + 5 triptans — high specificity) | 72 pos / 32 ctrl | - | - |
| **Systemic Lupus Erythematosus** | Yes | 4 cases validated (dx=32, meds=68 cross-indicated, labs [ANA≥160]=7, comp=70) | Yes (4-path + 5 SNOMED organ-involvement + 5 immunomodulators + ANA) | 72 pos / 32 ctrl | - | - |
| **Prostate Cancer** | Yes | 5 cases validated (dx=6, meds=6, labs [PSA>4]=3, **procedures [biopsy]=2 FOURTH**, comp=8) — **first male-only phenotype** | Yes (4-path + sex guard M + 5 SNOMED stages + 5 ADT/anti-androgens + biopsy + PSA) | 102 pos / 32 ctrl | - | - |
| **Epilepsy** | Yes | 4 cases validated (dx=46, meds=46, **procedures [EEG]=9 FIFTH**, comp=50) | Yes (3-path + 5 SNOMED subtypes + 5 AEDs + EEG) | 72 pos / 32 ctrl | - | - |
| **Peripheral Arterial Disease** | Yes | 3 cases validated (dx=24, meds=40 cross-indicated, comp=43) — **first peripheral vascular** | Yes (3-path + 5 SNOMED PAD forms + cilostazol/pentoxifylline + cross-indicated antiplatelets/statin) | 72 pos / 32 ctrl | - | - |
| **Pneumonia** | Yes | 4 cases validated (dx=37, meds=50 cross-indicated, **procedures [chest X-ray]=6 SIXTH**, comp=50) — **first acute infection** | Yes (3-path + 5 SNOMED etiologies + 5 antibiotics + first imaging procedure) | 72 pos / 32 ctrl | - | - |
| **Diabetic Retinopathy** | Yes | 4 cases validated (dx=30, meds [anti-VEGF]=21, **procedures [fundoscopy]=13 SEVENTH**, comp=32) — **first diabetes complication** | Yes (3-path + 5 SNOMED severity codes + 3 anti-VEGF + first ophthalmologic procedure) | 72 pos / 32 ctrl | - | - |
| **Ovarian Cancer** | Yes | 5 cases validated (dx=26, meds=26, labs [CA-125>35]=8, **procedures [oopho/hyster]=6 EIGHTH**, comp=29) — **first female-only phenotype** + **third 4-resource union** | Yes (4-path + sex guard F + 5 SNOMED histologies + 5 chemo + 2 surgical procedures + CA-125) | 142 pos / 62 ctrl | - | - |
| **NAFLD** | Yes | 3 cases validated (dx=33, labs [ALT/AST>40]=8, comp=33) — **first liver disease phenotype** | Yes (3-path + 5 SNOMED histologic stages + ALT/AST) | 72 pos / 32 ctrl | - | - |
| **Cataracts** | Yes | 3 cases validated (dx=15, **procedures [cataract surgery]=6 NINTH**, comp=15) — **first standalone lens disorder** + first ophthalmologic-surgical procedure | Yes (3-path + 4 SNOMED laterality/morphology + cataract surgery) | 72 pos / 32 ctrl | - | - |
| **Severe Childhood Obesity** | Yes | 3 cases validated (**dx=42** age-restricted via `patient.birthdate` chained search, labs [BMI≥30]=37, comp=52) — **first pediatric phenotype** (ages 5-17) using new `PatientFilters` schema | Yes (3-path + age guard 5-17 + 5 SNOMED severity codes + BMI≥30) | 352 pos / 102 ctrl | - | - |
| **Liver Cancer (HCC)** | Yes | 3 cases validated (dx=48 across primary/broader/metastatic SNOMED variants, labs [AFP≥100 ng/mL]=9, comp=50) — **fifth cancer + first liver malignancy** | Yes (3-path + 3 SNOMED variants + AFP) | 102 pos / 82 ctrl | - | - |
| **Benign Prostatic Hyperplasia** | Yes | 4 cases validated (dx=37 male+age40+, meds=42 [α-blocker/5-ARI], **procedures [TURP]=4 TENTH**, comp=47) — **second prostate** (differential dx vs PCa) + **first urologic-surgical** | Yes (4-path + sex M + age≥40 guards + tamsulosin/finasteride/terazosin + TURP) | 202 pos / 152 ctrl | - | - |
| **Peanut Allergy** | Yes | 3 cases validated (dx=43 pediatric 1-17, meds [epinephrine]=135 **largest cross-indication in suite**, labs [peanut IgE]=29) — **second pediatric** (reuses `PatientFilters`) + **first allergy/immunology** | Yes (3-path + age guard 1-17 + epinephrine 1660014 + peanut IgE 6206-7) | 252 pos / 202 ctrl | - | - |
| **Carotid Atherosclerosis** | Yes | 4 cases validated (dx=30, meds=61 heavy cross-indication, **procedures [carotid revasc]=6 ELEVENTH**, comp=68) — **first cerebrovascular precursor** + **first non-coronary vascular-surgical procedure** | Yes (4-path + age≥50 + carotid stenosis + aspirin/clopidogrel/atorvastatin + carotid angioplasty) | 100 pos / 80 ctrl | - | - |
| **Herpes Zoster (Shingles)** | Yes | 3 cases validated (dx=35, meds [acyclovir]=32, comp=42) — **first vaccine-preventable** + **first antiviral medication** + first dermatologic infection | Yes (3-path + age≥50 + zoster dx + acyclovir) | 100 pos / 80 ctrl | - | - |
| **Diverticulitis** | Yes | 3 cases validated (dx=31, meds [cipro+metro]=31, comp=40) — **second GI inflammatory** + **first antibiotic-treated phenotype** | Yes (3-path + age≥50 + diverticulitis dx + ciprofloxacin/metronidazole standard regimen) | 100 pos / 80 ctrl | - | - |
| **Tuberculosis** | Yes | 3 cases validated (dx=59, meds [rifampin+isoniazid]=77, comp=77) — **first chronic bacterial infection** + **first multi-drug regimen phenotype** (RIPE) | Yes (3-path + age≥18 + pulmonary/general TB + rifampin+isoniazid combo) | 100 pos / 80 ctrl | - | - |
| **Stroke (Cerebral Infarction)** | Yes | 3 cases validated (dx=31, meds [alteplase + antiplatelets]=67 **largest dx-meds ratio 2.2× from cross-indication**, comp=67) — **first cerebrovascular event** + **first thrombolytic** | Yes (3-path + age≥50 + stroke/CVA dx + alteplase + aspirin/clopidogrel) | 100 pos / 80 ctrl | - | - |
| **Osteoporosis** | Yes | 4 cases validated (dx=40, meds [bisphosphonates]=26, labs [DEXA T≤-2.5]=21, comp=45) — **first bone disease + first DEXA + first bisphosphonate** | Yes (3-path + age≥50 + osteoporosis dx + risedronate/zoledronate + DEXA T-score with negative-value-quantity filtering) | 100 pos / 80 ctrl | - | - |
| **Bipolar Disorder** | Yes | 3 cases validated (dx=72, meds [lithium/valproate/lamotrigine]=82, comp=100) — **first mood-stabilizer phenotype** + first lithium | Yes (3-path + age≥18 + bipolar dx + 3 mood stabilizers; comprehensive=100/100 paths fully exhaustive) | 100 pos / 80 ctrl | - | - |
| **Glaucoma** | Yes | 3 cases validated (dx=44 across 3 SNOMED variants OAG/PACG/broader, meds [timolol]=43, comp=54) — **second ophthalmology + first eye-drop medication** | Yes (3-path + age≥40 + 3 SNOMED variants + timolol) | 100 pos / 80 ctrl | - | - |
| **Lung Cancer** | Yes | 1 case validated (dx=29 across NSCLC/SCLC/broader SNOMED variants) — **sixth cancer phenotype**; chemo path skipped (oncology RxNorm 404s) | Yes (single-path + age≥50 + 3 SNOMED histology variants) | 100 pos / 80 ctrl | - | - |
| **Schizophrenia** | Yes | 3 cases validated (dx=72, meds [4 antipsychotics]=68, comp=81) — **first antipsychotic phenotype** (typical+atypical), 5th psychiatric | Yes (3-path + age≥18 + schizophrenia dx + haloperidol/risperidone/olanzapine/quetiapine) | 100 pos / 80 ctrl | - | - |
| **Gout** | Yes | 4 cases validated (dx=34, meds [allopurinol+colchicine]=56 large 22-pt Path C, labs [urate>7]=14, comp=62) — **first uric acid lab + first urate-lowering therapy** | Yes (4-path + age≥30 + gout dx + allopurinol/colchicine + urate>7 mg/dL) | 100 pos / 80 ctrl | - | - |
| **Iron Deficiency Anemia** | Yes | 4 cases validated (dx=52 across IDA+broader anemia, meds [ferrous sulfate]=73 21-pt Path C, labs [Hgb<12]=7, comp=74) — **first hematology + first ferritin/Hgb labs + first iron supplementation** | Yes (4-path + age≥18 + 2 SNOMED variants + ferrous sulfate SCD + Hgb/ferritin labs) | 100 pos / 80 ctrl | - | - |
| **Cervical Cancer** | Yes | 3 cases validated (dx=43 female-restricted, procedures [hysterectomy]=12, comp=47) — **second female-specific cancer** + reuses hysterectomy from ovarian | Yes (3-path + sex F + age≥21 + cervical ca dx + hysterectomy procedure) | 150 pos / 100 ctrl | - | - |
| **Pancreatic Cancer** | Yes | 3 cases validated (dx=47 across 2 SNOMED variants, labs [CA 19-9 >100]=16, comp=49) — **eighth cancer + first pancreatic + first CA 19-9 tumor marker** | Yes (3-path + age≥45 + 2 SNOMED variants + CA 19-9 lab) | 100 pos / 80 ctrl | - | - |
| **Hearing Loss** | Yes | 1 case validated (dx=33 across sensorineural/conductive/partial-deafness SNOMED variants) — **first sensory disorder phenotype** (dx-only, no meds/labs) | Yes (single-path + age≥50 + 3 SNOMED variants) | 100 pos / 80 ctrl | - | - |
| **Sepsis** | Yes | 4 cases validated (dx=66 across 3 SNOMED variants, meds [vanc+ceftriaxone]=78 12-pt Path C, labs [lactate>2]=7, comp=80) — **first septicemia phenotype**, complex multi-system | Yes (4-path + age≥18 + 3 SNOMED variants + vancomycin/ceftriaxone + lactate Sepsis-3 threshold) | 100 pos / 80 ctrl | - | - |
| **Cystic Fibrosis** | Yes | 1 case validated (dx=99 — **highest yield in suite**, single-SNOMED single-path module) — **first genetic pediatric phenotype** | Yes (single-path + age≥1 + CF dx; CFTR modulators + sweat chloride deferred) | 100 pos / 80 ctrl | - | - |
| **Bladder Cancer** | Yes | 1 case validated (dx=45) — **9th cancer + 2nd urological cancer** | Yes (single-path + age≥50 + bladder cancer dx; TURBT procedure + chemo deferred) | 100 pos / 80 ctrl | - | - |
| **Down Syndrome** | Yes | 1 case validated (dx=99 — ties CF for highest yield in suite) — **first chromosomal abnormality** (Trisomy 21) | Yes (single-path + age≥1 + Trisomy 21 dx) | 100 pos / 80 ctrl | - | - |
| **Polycystic Kidney Disease** | Yes | 1 case validated (dx=82) — **first hereditary kidney disease** | Yes (single-path + age≥18 + PKD infantile-type SNOMED — only verifiable variant) | 100 pos / 80 ctrl | - | - |
| **Fibromyalgia** | Yes | 3 cases validated (dx=61, meds [duloxetine/gabapentin/amitriptyline]=63, comp=78) — **first chronic pain syndrome** | Yes (3-path + age≥18 + fibromyalgia dx + 3 chronic-pain meds with cross-indication) | 100 pos / 80 ctrl | - | - |
| **Stomach (Gastric) Cancer** | Yes | 1 case validated (dx=41) — **10th cancer + 3rd GI cancer** | Yes (single-path + age≥50 + gastric cancer dx) | 100 pos / 80 ctrl | - | - |
| **Esophageal Cancer** | Yes | 1 case validated (dx=45) — **11th cancer + 4th GI cancer** | Yes (single-path + age≥50 + esophageal cancer dx) | 100 pos / 80 ctrl | - | - |
| **Renal Cell Carcinoma** | Yes | 1 case validated (dx=37) — **12th cancer + 3rd urological cancer** | Yes (single-path + age≥50 + clear-cell RCC dx) | 100 pos / 80 ctrl | - | - |
| **Glioblastoma** | Yes | 1 case validated (dx=61) — **13th cancer + 1st CNS malignancy** | Yes (single-path + age≥30 + GBM dx) | 100 pos / 80 ctrl | - | - |
| **Melanoma** | Yes | 1 case validated (dx=55) — **14th cancer + 1st skin cancer** | Yes (single-path + age≥30 + melanoma dx) | 100 pos / 80 ctrl | - | - |
| **Thyroid Cancer** | Yes | 1 case validated (dx=63) — **15th cancer + 1st endocrine malignancy** | Yes (single-path + age≥30 + thyroid cancer dx) | 100 pos / 80 ctrl | - | - |
| **Leukemia** | Yes | 1 case validated (dx=87) — **16th cancer + 1st hematologic malignancy** | Yes (single-path + age≥18 + broad leukemia dx covering AML/CML/ALL/CLL) | 100 pos / 80 ctrl | - | - |
| **Lymphoma** | Yes | 1 case validated (dx=83) — **17th cancer + 2nd hematologic malignancy** | Yes (single-path + age≥18 + broad lymphoma dx covering Hodgkin+NHL) | 100 pos / 80 ctrl | - | - |
| **Multiple Myeloma** | Yes | 1 case validated (dx=48) — **18th cancer + 3rd hematologic malignancy** | Yes (single-path + age≥45 + multiple myeloma dx) | 100 pos / 80 ctrl | - | - |
| **Hyperthyroidism (Graves')** | Yes | 4 cases validated (dx=63 across 2 SNOMED variants, meds [methimazole]=63, labs [TSH<0.1]=11, comp=64) — **first hyperthyroid phenotype** (counterpart to hypothyroidism) | Yes (3-path + age≥18 + 2 SNOMED variants + methimazole + suppressed TSH) | 100 pos / 80 ctrl | - | - |
| **Influenza** | Yes | 2 cases validated (dx=84, meds [oseltamivir]=69) — **acute viral respiratory infection** | Yes (3-path + age≥1 + influenza dx + oseltamivir) | 100 pos / 80 ctrl | - | - |
| **Lyme Disease** | Yes | 2 cases validated (dx=85, meds [doxycycline]=84) — **first vector-borne / tick-borne phenotype** | Yes (3-path + age≥1 + Lyme dx + doxycycline with heavy real-world cross-indication) | 100 pos / 80 ctrl | - | - |
| **COPD** | Yes | 3 cases validated (dx=50 across COPD+emphysema SNOMED variants, meds [albuterol+salmeterol]=44, comp=54) — **first chronic obstructive pulmonary phenotype** with bronchodilator cross-indication to asthma | Yes (3-path + age≥40 + 2 SNOMED variants + 2 bronchodilators) | 102 pos / 82 ctrl | - | - |
| **Ulcerative Colitis** | Yes | 3 cases revalidated 2026-04-30 (dx=186 cumulative, meds [mesalamine]=91, comp=196) — **third IBD phenotype**; switched from triamcinolone to mesalamine 5-ASA (proper first-line) after `get_source_atoms_for_cui` MCP tool unblocked code lookup | Yes (3-path + age≥15 + UC dx + mesalamine 52582) | 152 pos / 102 ctrl (+ residual triamcinolone-era data merged) | - | - |
| **Alcohol Use Disorder** | Yes | 3 cases validated (dx=65 across alcoholism+alcohol-dependence SNOMED variants, meds [naltrexone]=53, comp=79) — **first substance use disorder phenotype** | Yes (3-path + age≥18 + 2 SNOMED variants + naltrexone) | 102 pos / 82 ctrl | - | - |
| **Parkinson's Disease** | Yes | 3 cases validated (dx=56, meds [levodopa]=43, comp=67) — **first movement disorder phenotype**; levodopa is highly PD-specific | Yes (3-path + age≥50 + Parkinson's dx + levodopa) | 202 pos / 102 ctrl | - | - |
| **Psoriasis** | Yes | 3 cases validated (dx=100, meds [methotrexate]=85, comp=116) — **first immune-mediated skin disease**; heavy methotrexate cross-indication with RA | Yes (3-path + age≥18 + psoriasis dx + methotrexate SCD) | 152 pos / 102 ctrl | - | - |
| **Endometriosis** | Yes | 3 cases validated (dx=154 female-only, meds [leuprolide]=113, comp=166) — **first female non-cancer reproductive phenotype**; uses `patient.gender=female` filter | Yes (3-path + sex F + age 18-50 guards + endometriosis dx + leuprolide SCD) | 402 pos / 202 ctrl | - | - |
| **Clostridium difficile colitis** | Yes | 3 cases validated (dx=113, meds [vancomycin]=82, comp=123) — **first hospital-acquired infection**; vancomycin heavily cross-indicated with MRSA + other gram-positive | Yes (3-path + age≥18 + C. diff dx + vancomycin SCD) | 152 pos / 102 ctrl | - | - |
| **Chronic Rhinosinusitis** | Yes | 3 cases validated (dx=103, meds [mometasone]=77, comp=115) — **first ENT phenotype**; mometasone cross-indicated with allergic rhinitis, asthma, eczema | Yes (3-path + age≥18 + chronic sinusitis dx + mometasone) | 152 pos / 102 ctrl | - | - |
| **Intellectual Disability** | Yes | 1 case validated (dx=183 — highest single-path yield in suite tied with CF/Down) — **first general neurodevelopmental disability** distinct from autism + Down syndrome | Yes (single-path + age≥5 + intellectual disability dx) | 202 pos / 102 ctrl | - | - |
| **Urinary Incontinence** | Yes | 3 cases validated (dx=51, meds=46 across 3 antimuscarinics, comp=60) — **first non-cancer genitourinary phenotype**; tests multi-RxNorm (oxybutynin/tolterodine/solifenacin) — codes resolved via new `get_source_atoms_for_cui` MCP tool after batch 24 pivot | Yes (3-path + age≥50 + UI dx + 3 antimuscarinics) | 202 pos / 102 ctrl | - | - |
| **Community-Acquired MRSA** | Yes | 3 cases validated (dx=106, meds [clindamycin+linezolid]=82, comp=119) — **first MRSA-specific phenotype**; clindamycin cross-indicated with anaerobic infections, linezolid with VRE | Yes (3-path + age≥18 + CA-MRSA dx + clindamycin/linezolid) | 152 pos / 102 ctrl | - | - |
| **Functional Seizures (PNES)** | Yes | 1 case validated (dx=120 — Dissociative convulsions SNOMED) — **first psychogenic neurologic phenotype** distinct from epilepsy; modeled with no medications by design (PNES managed by psychotherapy) | Yes (single-path + age≥18 + PNES dx) | 152 pos / 102 ctrl | - | - |
| **Steroid-Induced Osteonecrosis** | Yes | 3 cases validated (dx=111, meds [prednisone]=83, comp=122) — **first iatrogenic bone disease**; tests massive prednisone cross-indication (most prednisone users do NOT develop AVN — models complication-tracking workflow) | Yes (3-path + age≥30 + drug-induced AVN dx + prednisone) | 202 pos / 102 ctrl | - | - |
| **Drug-Induced Liver Injury (DILI)** | Yes | 4 cases validated (dx multi-system [SNOMED+3 ICD-10]=163, labs [ALT≥225]=40, meds [methotrexate]=365, comp=370) — **first PheKB-aligned batch via new skill**; multi-system code list 2.7× boosts recall vs SNOMED-only | Yes (4-path + age≥18 + 4 dx codes + ALT/AST/ALP/Bili thresholds + methotrexate) | 202 pos / 102 ctrl | - | - |
| **Resistant Hypertension** | Yes | 4 cases validated (dx=82, meds [4-class]=106, labs [SBP>140]=13, comp=106) — **PheKB-aligned eMERGE Type-1/Type-2**; 4-drug regimen test (lisinopril+amlodipine+HCTZ+spironolactone) | Yes (3-path + age≥40 + dx + 4 antihypertensives + SBP threshold) | 202 pos / 102 ctrl | - | - |
| **Neonatal Abstinence Syndrome** | Yes | 3 cases validated (dx multi-system [SNOMED+P96.1]=338, meds [morphine]=343, comp=464) — **first neonatal phenotype**; multi-system 1.8× boosts recall (infant-side indicators only — Synthea can't model maternal-infant dyads) | Yes (3-path + age≤1 + 2 dx codes + morphine) | 252 pos / 102 ctrl | - | - |
| **Developmental Language Disorder (APT-DLD)** | Yes | 1 case validated (dx multi-code [F80.1+F80.2+F80.89]=187) — **first speech/language pediatric phenotype**; aligned to APT-DLD algorithm (Walters et al. 2020) | Yes (single-path + age 5-17 + 3 ICD-10 codes; no meds path — DLD is treated with speech therapy) | 202 pos / 102 ctrl | - | - |
| **Febrile Neutropenia (Pediatric)** | Yes | 4 cases validated (dx [D70]=180, labs [ANC<0.5]=15, meds [cefepime]=200, comp=200) — **first pediatric oncology complication**; aligned to PheKB ELSA-FN trial algorithm | Yes (3-path + age≤17 + neutropenia/fever dx + ANC + Temp + cefepime) | 202 pos / 102 ctrl | - | - |
| **Statins and MACE** | Yes | 4 cases validated (dx multi-system [SNOMED+I21.0+I21.9]=75, labs [Trop≥0.10]=14, meds [atorvastatin]=96, comp=96) — **first cardiovascular outcomes phenotype**; aligned to PheKB BioVU AMI algorithm (Wei, Denny et al.) | Yes (3-path + age≥40 + 3 AMI codes + atorvastatin + Troponin I threshold) | 202 pos / 102 ctrl | - | - |
| **Warfarin Dose Response** | Yes | 3 cases validated (meds [warfarin]=98, labs [INR 2-3]=16, comp=98) — **first PGx phenotype**; aligned to PheKB BioVU pharmacogenetic algorithm (target INR 2-3 over 3+ weeks) | Yes (3-path + age≥40 + warfarin + INR observations stable/supra/sub-therapeutic) | 202 pos / 102 ctrl | - | - |
| **Clopidogrel Poor Metabolizers** | Yes | 2 cases validated (meds [clopidogrel]=88, comp [clopidogrel + AMI]=137) — **second PGx phenotype**; aligned to PheKB Vanderbilt VESPA algorithm | Yes (3-path + age≥40 + clopidogrel + Drug_Delay + AMI dx) | 202 pos / 102 ctrl | - | - |
| **Multimodal Analgesia** | Yes | 1 case validated (meds [opioid+NSAID+APAP union]=159) — **first care-pattern phenotype**; aligned to PheKB Stanford algorithm (postop multimodal regimen) | Yes (3-path + age≥18 + surgical encounter + 3 analgesic classes) | 202 pos / 102 ctrl | - | - |
| Coronary Heart Disease (legacy) | No | 1 (basic) | No | No | - | - |
| Coronary Heart Disease | No | 1 (basic) | No | No | - | - |
| *... 89 more phenotypes* | No | 1 (basic) | No | No | - | - |

## Phenotypes Pending PheKB-Doc Revision (T1)

The audit at `docs/PHENOTYPE-AUDIT.md` classifies 63 phenotypes as **T1-significant-gap**: their PheKB doc lists ≥8 codes, lab thresholds, or temporal logic that the current modules under-model (typically just 1 SNOMED dx, missing the 8-60+ ICD-9/ICD-10 variants real EHR data contains).

**Already revised with PheKB-doc-first workflow (batches 26-32, 16 phenotypes + 2 doc-reviewed — exclude from revision):**
- Batch 26: drug-induced-liver-injury, resistant-hypertension, neonatal-abstinence-syndrome
- Batch 27: developmental-language-disorder, febrile-neutropenia-pediatric, statins-and-mace
- Batch 28: warfarin-dose-response, clopidogrel-poor-metabolizers, multimodal-analgesia
- Batch 29: cardiac-conduction-qrs, autoimmune-disease, asthma-response-inhaled-steroids
- Batch 30: cardiorespiratory-fitness, bone-scan-utilization, digital-rectal-exam
- Batch 31: liver-cancer-staging, post-event-pain
- Batch 32: abdominal-aortic-aneurysm (multi-coded via code-augmentation pipeline — SNOMED + ICD-10 + ICD-9 + CPT); ace-inhibitor-cough (PheKB has no codes — doc-reviewed); acute-kidney-injury (PheKB's only code already in module — doc-reviewed)
- Batch 33: adhd (multi-coded SNOMED + ICD-10 F90.x + ICD-9 314.x); appendicitis (multi-coded SNOMED + ICD-10 K35.x + ICD-9 540); anxiety (PheKB has no extracted codes — doc-reviewed)
- Batch 34: asthma (multi-coded SNOMED + ICD-10 J45.x + ICD-9 493.x); atopic-dermatitis (multi-coded SNOMED + ICD-10 L20.9/L30.9 + ICD-9 691.8/692.9); autism (multi-coded SNOMED + ICD-10 F84.0/F84.5/F84.9 + ICD-9 299.x)
- Batch 35: bph (multi-coded SNOMED + ICD-10 N40.0 + ICD-9 600.00, plus CPT 52601 TURP); breast-cancer (multi-coded SNOMED + ICD-10 C50.91x + ICD-9 174.x — replaced bad auto-populator V10.3 history-of-cancer entry); ca-mrsa (multi-coded SNOMED + ICD-10 A49.02 + ICD-9 041.12 — replaced too-narrow pneumonia 482.42 entry). Augmentation map cleanup also done: replaced bad auto-populator matches for Crohn's (was Reiter's-disease 099.3 → now K50.x/555.x), carotid 233259003 (was dx 433.1 → now CPT 37215 stent), diverticulitis (removed non-FHIR HICDA system entry → now K57.92).
- Batch 36: carotid-atherosclerosis (64586002 → ICD-10 I65.29 + ICD-9 433.1; 233259003 → CPT 37215); chronic-rhinosinusitis (40055000 → ICD-10 J32.9 + ICD-9 473.9); ckd (5 SNOMED stages → ICD-10 N18.x + ICD-9 585.x family).
- Batch 37: colorectal-cancer (5 SNOMEDs → C18.x/C19); coronary-heart-disease (5 dx SNOMEDs → I25.x; 4 procedure SNOMEDs → CPT 33533/92928/92920); crohns-disease (5 SNOMEDs → K50.x + 555.x).
- Batch 38: dementia (Alzheimer's → G30.9, vascular → F01.50, frontotemporal → G31.09, Lewy body → G31.83, general → F03.90 — replaced bad auto-populator 290.10 entries); depression (5 SNOMEDs → F32.A/F33.9/F32.9/F34.1 + 311/296.x/300.4); diabetic-retinopathy (5 dx SNOMEDs → E11.319/E11.329/E11.359/E11.311; fundoscopy → CPT 92250).
- Batch 39: diverticulitis (already done batch 36); epilepsy (5 SNOMEDs → G40.x/R56.9; EEG → CPT 95816); familial-hypercholesterolemia (5 SNOMEDs → E78.01).
- Batch 40: functional-seizures (191714002 → F44.5 + 300.11); gerd (3 SNOMEDs → K21.9 + 530.81); heart-failure (5 SNOMEDs → I50.x + 428.x — replaced bad 428.X wildcard).
- Batches 41-49 (bulk): herpes-zoster, hiv (4 SNOMEDs), hypertension (5 SNOMEDs → I10), intellectual-disability, lung-cancer (3 SNOMEDs), migraine (5 SNOMEDs — replaced wildcards), multiple-sclerosis (5 SNOMEDs → G35), nafld (5 SNOMEDs → K75.81/K76.0), ovarian-cancer (5 dx + 2 procedure SNOMEDs), peanut-allergy, peripheral-arterial-disease (5 SNOMEDs → I73.9), pneumonia (5 dx SNOMEDs + chest X-ray CPT), prostate-cancer (5 dx + biopsy CPT 55700), severe-childhood-obesity (5 SNOMEDs), sickle-cell-disease (3 SNOMEDs → D57.x), steroid-induced-avn, systemic-lupus-erythematosus (5 SNOMEDs → M32.x), type-1-diabetes (5 SNOMEDs → E10.x — replaced wildcard), type-2-diabetes (3 SNOMEDs → E11.x — replaced wildcard), urinary-incontinence, venous-thromboembolism (5 SNOMEDs → I82.x/I26.99 — replaced wildcards).

**Augmentation map total: 314 entries** across all 48 T1 revision phenotypes. All 33 remaining phenotypes augmented + reloaded to Microsoft FHIR (background job, ~hours). Final validation step: `for p in <slug>; do FHIR_BASE=https://localhost:8443 python scripts/validate_phenotype_test_cases.py $p; done` after reload completes.

**Migrated from HAPI to Microsoft Health FHIR Server (2026-05-01)**: Persistent HAPI instability under rapid sequential loads led to switching to the Microsoft OSS FHIR Server (`healthcareapis/r4-fhir-server:latest`, port 8443 HTTPS, SQL Server backed). Required `FhirServer__Security__Enabled=false`, `FhirServer__Bundle__EntryLimit=5000`, and placeholder `FhirServer__Security__Authentication__Authority` env vars; commented out `TestAuthEnvironment__FilePath` to avoid auth-provider DI errors. Patched `backend/src/fhir/client.py` (added `verify_ssl` param + auto-detect Microsoft FHIR's root-mounted endpoint when port 8443 / https URL), `cli/fhir_eval/commands/load.py` (added `--insecure` and `--fhir-path` flags), and `scripts/validate_phenotype_test_cases.py` (reads `FHIR_BASE` env var). Reload commands now use `--fhir-url https://localhost:8443` and `FHIR_BASE=https://localhost:8443`. Full reload of all 108 phenotypes completed clean (20,206 patients, 0 errors).

**Code-augmentation pipeline (new 2026-05-01)**: Synthea's FHIR exporter only emits the first coding per resource, so multi-system codes can't be added directly to modules. New pipeline:
- `data/code_augmentations.json` — SNOMED-keyed crosswalk map
- `scripts/build_code_augmentations.py` — one-shot populator from PheKB docs
- `scripts/augment_fhir_codes.py` — post-process Synthea bundles in-place

Workflow becomes: synthea generate → augment_fhir_codes.py → fhir-eval load → validate.

### Agentic-loop improvements TODO (insights from Tier 1 sweep)

10 insights from designing 108 phenotypes + 314 augmentation entries that should reshape the agentic loop. Priority 1 + 2 done 2026-05-03; the rest are queued.

- [x] **#1 — Multi-coded data is the rule.** Bake into system prompt: real Conditions/Procedures/Observations carry SNOMED + ICD-10 + ICD-9 + CPT simultaneously; sample server before committing to a code system. Done in `agentic_provider.py` system prompt.
- [x] **#2 — Code-family enumeration via VSAC.** System prompt now elevates `vsac_search_value_sets` + `vsac_expand_value_set` to the canonical first step; calls out cancers/dementias/diabetes as needing full subtype lists.
- [x] **#3 — Multi-resource union for provider-level cohorts.** Decomposition step (Condition/MedicationRequest/Observation/Procedure) added to system prompt with explicit "documented via dx only / treated but undocumented / lab-evidenced / procedure-evidenced" framing.
- [x] **#4 — Threshold logic on Observations.** `value-quantity` examples (`ge6.5||%25`, `ge2.0||mg/dL`) now in system prompt.
- [x] **#5 — Patient-level filters via chained search.** Examples for `patient.gender`, `patient.birthdate` in system prompt.
- [x] **#6 — Negation and exclusion via two-query subtraction.** Done 2026-05-03. Runner-side support was already wired (`evaluate_multi_query_patient_difference` in `backend/src/evaluation/execution.py`, dispatched via `metadata.negation` flag in `runner.py:160`). What was missing: the validator script (`scripts/validate_phenotype_test_cases.py`) was applying union semantics to ALL multi-query cases, including negation ones, so refreshed `expected_patient_ids` were computed via union instead of difference. Patched validator to honor `negation: true` and apply set difference. Re-validated 4 negation test cases against Microsoft FHIR: Crohn's biologic-without-dx (19 patients), sleep-apnea polysom-without-dx (2), T1D insulin-without-dx (4), VTE anticoag-without-dx (106). Runner pathway and validator now match — LLM evaluation against these tests will score correctly.
- [x] **#7 — Cross-resource references (`_has`, `_include`, `_revinclude`).** Examples added to system prompt. The 5 cross-resource test cases should be exercisable now.
- [x] **#8 — VSAC-before-UMLS strategy.** Workflow reordered: VSAC first, sample data second, UMLS only as fallback for rare phenotypes.
- [x] **#9 — Iterate: query → count → refine.** "Core principles" section in system prompt explicitly instructs sample-and-validate.
- [x] **#10 — Tier 3 phenotype methodology skill.** Done 2026-05-03. `backend/src/llm/tier3_methodology.md` written — 12 playbooks covering disease-with-subtypes, PGx, pediatric/sex-restricted, iatrogenic, procedural, threshold-based, multi-system PheKB code lists, acute/temporal, negation, cross-resource AND, and cohort-vs-case decisions. Plus a categorization decision tree and a worked T2D example. Agentic provider now accepts a `tier` kwarg (default 2); `tier=3` prepends the methodology to the system prompt. CLI `--tier` flag added to `fhir-eval run`.

**Test matrix (3 prompts × 3 tiers × 3 data tracks × N models):**
- Prompt variants: `naive` / `broad` / `expert` — `broad` now unlocked in CLI as of 2026-05-03 (was previously only naive/expert).
- Tiers: 1 (closed book, `provider.py`), 2 (agentic with tools, `agentic_provider.py`), 3 (agentic + IG-aware reading + methodology skill — pending #10).
- Data tracks: Synthea Generic (current default), Synthea US Core variant (planned `*_uscore.json` modules), MIMIC-IV (planned).

### Known: Reload duplicates on Microsoft FHIR

Synthea transaction bundles use POST with relative URLs, not PUT-with-ID. Each reload creates NEW resources on Microsoft FHIR rather than upserting. Validation still produces correct unique-patient counts because the validator maps HAPI patient IDs back to the stable Synthea UUIDs via `Patient.identifier`, so duplicates collapse. But raw resource counts accumulate (e.g., AAA shows 46 Conditions for 23 unique patients after 2 reloads).

Two paths to clean this up later:
- Wipe phenotype resources before each reload (`DELETE` by Patient compartment)
- Switch to `$import` (which has deduplication via `ImportMode=IncrementalLoad`) — see TODO below

For now, accept the duplication during the revision sweep — validation still works correctly.

### TODO: Bulk-load via Microsoft FHIR `$import` + Azurite (next reload)

Switched from HAPI to the Microsoft Health FHIR Server (image `healthcareapis/r4-fhir-server:latest`, port 8443 HTTPS, SQL-backed). Reliable but slow on transaction-bundle ingest — ~10-12 hrs to reload all 108 phenotypes via per-bundle POSTs (SQL Server pegged at 95% CPU during ingest).

For future full reloads, use `$import`:
1. Convert augmented Synthea bundles to **NDJSON shards per resource type** (Patient.ndjson, Condition.ndjson, Procedure.ndjson, MedicationRequest.ndjson, Observation.ndjson, etc.) — one resource per line.
2. Upload shards to the Azurite blob container (already running at port 10000, env var `STORAGE_ACCOUNT_CONNECTION=UseDevelopmentStorage=true`).
3. POST a `Parameters` resource to `https://localhost:8443/$import` referencing the shard URLs. Microsoft FHIR runs the import async, returns a status URL to poll.
4. Bulk import bypasses the per-bundle transaction overhead — typically 10x+ faster than `fhir-eval load synthea`.

Tooling needed (build before next reload):
- `scripts/synthea_to_ndjson.py` — walk `synthea/output/*/{positive,control}/fhir/*.json`, group entries by resourceType, emit shard files
- `scripts/upload_ndjson_to_azurite.py` — push shards to local Azurite container
- `scripts/import_ndjson_to_fhir.py` — orchestrate the `$import` request + status polling

Reference: https://learn.microsoft.com/en-us/azure/healthcare-apis/fhir/configure-import-data and the `microsoft/fhir-server` repo `samples/` for `$import` request format.

**State-B PheKB extraction (2026-05-02)** — 6 previously-unanalyzed phenotypes (`atrial-fibrillation-demonstration-project`, `cardiac-conduction-qrs`, `cataracts`, `clostridium-difficile-colitis`, `hypothyroidism`, `rheumatoid-arthritis-demonstration-project`) had their PheKB algorithm `.doc` files extracted via Claude streaming (`scripts/extract_phekb_doc_analysis.py`). 836 new PheKB-listed codes captured. State A is now 69/108 (was 63), State B is 0. 5 of 6 picked up new augmentation entries (cardiac-conduction-qrs already covered). 22 test cases re-validated post-reload, all pass. Doc audit at `docs/PHENOTYPE-DOC-AUDIT.md`.

**Tier 1 revision sweep COMPLETE (2026-05-02)** — task #167 closed. All 48 T1 phenotypes augmented with PheKB-doc-derived ICD-10/ICD-9/CPT codings. Final validation: 113 test cases across 30 batch-38-49 phenotypes all pass on Microsoft FHIR; 18 batch-32-37 phenotypes validated incrementally during the sweep. Total augmentation map: 314 SNOMED-keyed entries. Workflow established (`scripts/build_code_augmentations.py` + `scripts/augment_fhir_codes.py` + `data/code_augmentations.json`) is reusable for future PheKB-doc-first phenotypes added to the suite.

| # | Phenotype | PheKB raw dir | PheKB code count | Thresholds? | Temporal? |
|---|---|---|---|---|---|
| 1 | abdominal-aortic-aneurysm | abdominal-aortic-aneurysm-aaa | CPT:16, ICD-9-CM:11 | yes | yes |
| 2 | ace-inhibitor-cough | ace-inhibitor-ace-i-induced-cough | (in algorithm text) | no | no |
| 3 | acute-kidney-injury | acute-kidney-injury-aki | LOINC:1 | yes | yes |
| 4 | adhd | adhd-phenotype-algorithm | ICD-9-CM:38 | no | no |
| 5 | anxiety | anxiety-algorithm | (in algorithm text) | no | no |
| 6 | appendicitis | appendicitis | ICD-9-CM:40, SNOMED CT:37, CPT:9 | no | no |
| 7 | asthma | asthma | ICD-9-CM:37 | no | no |
| 8 | atopic-dermatitis | atopic-dermatitis-algorithm | ICD-9-CM:34 | yes | no |
| 9 | autism | autism | ICD-9-CM:9 | no | no |
| 10 | bph | phema-bph-benign-prostatic-hyperplasia-cases | ICD-9-CM:2, RxNorm:1, CPT:1 | no | no |
| 11 | breast-cancer | breast-cancer | ICD-9-CM:1 | yes | no |
| 12 | ca-mrsa | camrsa | ICD-9-CM:8 | no | yes |
| 13 | carotid-atherosclerosis | caad-carotid-artery-atherosclerosis-disease | ICD-9-CM:4, CPT:1 | no | no |
| 14 | chronic-rhinosinusitis | crs-chronic-rhinosinusitis | ICD-9-CM:2 | yes | no |
| 15 | ckd | chronic-kidney-disease | CPT:1 | yes | yes |
| 16 | colorectal-cancer | colorectal-cancer-crc | ICD-10-CM:63 | no | yes |
| 17 | coronary-heart-disease | coronary-heart-disease-chd | SNOMED CT:9, ICD-10-CM:7, CPT:5, ICD-9-CM:1 | no | no |
| 18 | crohns-disease | crohns-disease-demonstration-project | ICD-9-CM:55 | yes | no |
| 19 | dementia | dementia | ICD-9-CM:23 | no | yes |
| 20 | depression | depression | ICD-9-CM:1, ICD-10-CM:1 | no | no |
| 21 | diabetic-retinopathy | diabetic-retinopathy | (in algorithm text) | no | no |
| 22 | diverticulitis | diverticulosis-and-diverticulitis | CPT:58, ICD-9-CM:8, HICDA:4 | no | yes |
| 23 | epilepsy | epilepsyantiepileptic-drug-response-algorithm | ICD-10-CM:51, ICD-9-CM:46 | yes | no |
| 24 | familial-hypercholesterolemia | electronic-health-record-based-phenotyping-algorithm-familial-hypercholesterolemia | ICD-9-CM:40, ICD-10-CM:25, CPT:2, HCPCS:1 | no | no |
| 25 | functional-seizures | functional-seizures | ICD-9-CM:8, ICD-10-CM:6, CPT:2 | no | no |
| 26 | gerd | gastroesophageal-reflux-disease-gerd-phenotype-algorithm | ICD-9-CM:34 | yes | no |
| 27 | heart-failure | heart-failure-hf-differentiation-between-preserved-and-reduced-ejection-fraction | ICD-9-CM:1, SNOMED CT:1 | yes | yes |
| 28 | herpes-zoster | herpes-zoster | (in algorithm text) | no | yes |
| 29 | hiv | hiv | LOINC:38 | no | no |
| 30 | hypertension* | blood-pressure | ICD-10-CM:1 | no | no |
| 31 | intellectual-disability | intellectual-disability | ICD-10-CM:92, ICD-9-CM:42 | no | no |
| 32 | lung-cancer* | computable-phenotypes-identifying-patients-lung-and-gastroenteropancreatic-neuroendocrine | ICD-10-CM:30, ICD-9-CM:26 | no | no |
| 33 | migraine | migraine | ICD-9-CM:25, ICD-10-CM:24 | yes | no |
| 34 | multiple-sclerosis | multiple-sclerosis-demonstration-project | ICD-9-CM:68 | no | no |
| 35 | nafld | non-alcoholic-fatty-liver-disease-nalfd-alcoholic-fatty-liver-disease-ald | ICD-9-CM:14, ICD-10-CM:11, LOINC:4 | no | no |
| 36 | ovarian-cancer | ovarianuterine-cancer-ovutca | ICD-10-CM:5 | yes | yes |
| 37 | peanut-allergy | peanut-allergy | CPT:8 | no | no |
| 38 | peripheral-arterial-disease | peripheral-arterial-disease-2012 | ICD-9-CM:23, CPT:18 | yes | no |
| 39 | pneumonia | pneumonia-vumc-emerge-v51 | RxNorm:1 | no | yes |
| 40 | prostate-cancer | prostate-cancer-0 | (in algorithm text) | no | no |
| 41 | severe-childhood-obesity | severe-early-childhood-obesity | ICD-9-CM:65 | yes | no |
| 42 | sickle-cell-disease | sickle-cell-disease-0 | ICD-9-CM:10 | no | no |
| 43 | steroid-induced-avn | steroid-induced-osteonecrosis | ICD-9-CM:49, CPT:40 | no | no |
| 44 | systemic-lupus-erythematosus | sle-systemic-lupus-erythematosus-using-slicc-systemic-lupus-internation-collaborating | ICD-10-CM:14, LOINC:11, ICD-9-CM:10, RxNorm:6, CPT:1 | no | yes |
| 45 | type-1-diabetes | type-1-and-type-2-diabetes-mellitus | RxNorm:33, LOINC:7, ICD-10-CM:2, ICD-9-CM:1 | yes | no |
| 46 | type-2-diabetes | type-2-diabetes-t2d | SNOMED CT:9, LOINC:9, ICD-9-CM:8, ICD-10-CM:7 | yes | no |
| 47 | urinary-incontinence | urinary-incontinence | ICD-9-CM:1, ICD-10-CM:1, CPT:1 | yes | no |
| 48 | venous-thromboembolism | venous-thromboembolism-vte | ICD-9-CM:36 | no | no |

\* `hypertension` maps to PheKB `blood-pressure`, which is a BP-measurement-processing algorithm rather than an HTN cohort definition — review may yield no actionable revision.
\* `lung-cancer` maps to a PheKB lung+GEP-neuroendocrine phenotype; only partial scope match.

**T3-aligned (9 phenotypes)**: atrial-fibrillation, cardiac-conduction-qrs, cataracts, clostridium-difficile, febrile-neutropenia-pediatric, fibromyalgia, hypothyroidism, rheumatoid-arthritis, sleep-apnea — PheKB doc has minimal extracted codes; module probably acceptable but worth a quick doc review.

**T3-no-phekb (36 phenotypes — no PheKB doc available; cannot revise)**:
alcohol-use-disorder, bipolar-disorder, bladder-cancer, cervical-cancer, copd, cystic-fibrosis, down-syndrome, endometriosis, esophageal-cancer, glaucoma, glioblastoma, gout, hearing-loss, hepatitis-c, hyperthyroidism, influenza, iron-deficiency-anemia, leukemia, liver-cancer, lyme-disease, lymphoma, melanoma, multiple-myeloma, osteoporosis, pancreatic-cancer, parkinsons-disease, polycystic-kidney-disease, psoriasis, renal-cancer, schizophrenia, sepsis, stomach-cancer, stroke, thyroid-cancer, tuberculosis, ulcerative-colitis

Regenerate the audit anytime: `python scripts/audit_phenotypes_vs_phekb.py` → outputs `docs/PHENOTYPE-AUDIT.md`.

### Tier 1 vs Tier 2 Comparison (qwen2.5:7b, all 34 test cases)

First batch evaluation run on 2026-03-15. Tier 1 = closed book (no tools). Tier 2 = agentic with FHIR server tools + hardcoded code lookup table (UMLS integration added after this run).

| Test Case | Complexity | T1 F1 | T2 F1 | T2 Tools | Winner |
|-----------|-----------|:-----:|:-----:|:--------:|--------|
| **Diagnosis queries (easy)** | | | | | |
| aaa-dx | easy | 0.00 | 0.00 | 5 | tie |
| ace-inhibitor-cough-dx | medium | 0.00 | 1.00 | 3 | **T2** |
| adhd-dx | easy | 0.00 | 1.00 | 3 | **T2** |
| aki-dx | easy | 0.00 | 1.00 | 2 | **T2** |
| anxiety-dx | easy | 0.00 | 0.00 | 3 | tie |
| appendicitis-dx | easy | 0.00 | 1.00 | 3 | **T2** |
| asthma-dx | easy | 0.00 | 1.00 | 3 | **T2** |
| atopic-dermatitis-dx | easy | 0.00 | 0.00 | 5 | tie |
| atrial-fibrillation-dx | easy | 0.00 | 1.00 | 5 | **T2** |
| autism-dx | easy | 0.00 | 0.00 | 4 | tie |
| type-2-diabetes-dx | easy | 0.00 | 0.00 | 3 | tie |
| **Medication queries (medium)** | | | | | |
| ace-inhibitor-cough-meds | medium | 0.00 | 0.00 | 4 | tie |
| adhd-meds | medium | 0.00 | 0.00 | 0 | tie |
| anxiety-meds | medium | 0.00 | 0.00 | 4 | tie |
| asthma-meds | medium | 0.00 | 0.00 | 0 | tie |
| atopic-dermatitis-meds | medium | 0.00 | 0.00 | 6 | tie |
| atrial-fibrillation-meds | medium | 0.00 | 0.00 | 5 | tie |
| autism-meds | medium | 0.00 | 0.00 | 5 | tie |
| type-2-diabetes-meds | medium | 0.00 | 0.00 | 6 | tie |
| **Lab/Procedure queries (hard)** | | | | | |
| aki-labs | hard | 1.00 | 0.00 | 2 | T1 |
| type-2-diabetes-labs | hard | 0.00 | 0.00 | 3 | tie |
| appendicitis-procedures | medium | 0.00 | 0.00 | 4 | tie |
| type-2-diabetes-path4 | expert | 0.00 | 0.00 | 4 | tie |
| **Comprehensive (multi-query)** | | | | | |
| aaa-comprehensive | expert | 0.00 | 1.00 | 18 | **T2** |
| ace-inhibitor-cough-comp | expert | 0.00 | 0.00 | 0 | tie |
| adhd-comprehensive | expert | 0.00 | 0.00 | 17 | tie |
| aki-comprehensive | expert | 0.00 | 0.00 | 3 | tie |
| anxiety-comprehensive | expert | 0.00 | 0.00 | 6 | tie |
| appendicitis-comprehensive | expert | 0.00 | 0.00 | 4 | tie |
| asthma-comprehensive | expert | 0.00 | 1.00 | 6 | **T2** |
| atopic-dermatitis-comp | expert | 0.00 | 1.00 | 10 | **T2** |
| atrial-fibrillation-comp | expert | 0.00 | 0.00 | 6 | tie |
| autism-comprehensive | expert | 0.00 | 0.00 | 4 | tie |
| type-2-diabetes-comp | expert | 0.00 | 0.00 | 7 | tie |
| | | | | | |
| **AVERAGE** | | **0.03** | **0.26** | | |
| **Tier 2 wins** | | | | | **9** |
| **Tier 1 wins** | | | | | **1** |
| **Ties** | | | | | **24** |

### Evaluation Reporting Gap

The current evaluation produces a **single F1 score** per test case, making it impossible to diagnose WHERE in the reasoning chain the LLM failed. A three-layer evaluation decomposition has been designed to address this — see `docs/IMPLEMENTATION-ROADMAP.md` for the full specification and `docs/literature_review.md` for the literature analysis that motivated it.

### Key Findings

1. **Tier 2 (agentic) is 9x better** on average F1 (0.265 vs 0.029)
2. **Diagnosis queries**: Tier 2 scored perfect 1.0 on 6/11 dx queries vs 0/11 for Tier 1
3. **Medication queries**: Both tiers scored 0.00 on ALL medication queries — root cause: hardcoded lookup table only had ingredient-level codes, not the SCD codes in the data. **Fixed** by wiring in real UMLS API with crosswalk support.
4. **Comprehensive queries**: Tier 2 scored 3 perfect scores (AAA, asthma, atopic dermatitis)
5. **Tier 1's one win**: AKI labs — qwen2.5:7b happened to know the LOINC code for creatinine
6. **qwen2.5:7b limitations**: Even with tools, the 7b model struggles with multi-step reasoning and query syntax

### Failure Analysis

| Failure Mode | Tier 1 | Tier 2 | Fix Applied |
|-------------|:------:|:------:|-------------|
| Wrong clinical codes (hallucinated) | 100% of failures | Rare | Tools provide real codes |
| Wrong resource type | Common | Rare | Server sampling shows what exists |
| Malformed query syntax | Common | Occasional | System prompt improvements |
| Ingredient vs SCD code mismatch | N/A | 100% of med failures | UMLS crosswalk integration |
| MedicationOrder (STU3) vs MedicationRequest (R4) | Occasional | Occasional | Auto-correction added |

## What's Built

### FHIR Servers

| Server | Port | Command | Status |
|--------|------|---------|--------|
| **HAPI FHIR** (default) | 8080 | `docker-compose up -d fhir-server` | Working |
| **Azure FHIR** | 9080 | `docker-compose up -d azure-fhir` | Configured (needs SQL Server) |

### Evaluation Pipeline

- **Multi-query support**: Test cases with `multi_query: true` evaluated by unioning patient IDs across all generated queries
- **Patient-level scoring**: Comprehensive test cases compare patient IDs across multiple FHIR resource types
- **Query coverage scoring**: Checks how many expected resource types the LLM searched
- **Multi-query parser**: Extracts all FHIR queries from an LLM response
- **Batch runner**: `run_batch_eval.py` runs all test cases through both tiers with summary table
- **Agentic evaluation**: `OllamaAgenticProvider` with tool calling loop

### LLM Providers

| Provider | Command | Status | Cost |
|----------|---------|--------|------|
| Anthropic SDK | `-p anthropic` | Credits depleted | API credits |
| Claude CLI | `-p claude-cli` | `--print` requires API credits | API credits |
| Ollama (closed book) | `-p command --command "ollama run <model>"` | Working | Free |
| **Ollama (agentic)** | `-p ollama-agentic -m <model>` | **Working** | Free |

### Evaluation Tiers

| Tier | LLM Has Access To | Status |
|------|-------------------|--------|
| **1. Closed Book** | Just the prompt | **Working** — batch results above |
| **2. Tool-Assisted** | + UMLS API (search + crosswalk) + FHIR server tools | **Working** — batch results above |
| **3. Skill-Guided** | + IG profiles (FSH/YAML) + valueset bindings + VSAC | Design complete |

### Agentic Tools (Tier 2)

| Tool | Purpose | Implementation |
|------|---------|---------------|
| `umls_search` | Search NIH UMLS for clinical concepts → codes | Real UMLS API via `nih-umls-mcp` |
| `umls_crosswalk` | Map codes between systems (ingredient→SCD, SNOMED→ICD-10) | Real UMLS API |
| `fhir_server_metadata` | Query CapabilityStatement for supported resources/params | HTTP to HAPI FHIR |
| `fhir_resource_sample` | Spot-check what code systems are in the data | HTTP to HAPI FHIR |
| `fhir_search` | Test a FHIR query and see results summary | HTTP to HAPI FHIR |

### Skills

| Skill | Purpose |
|-------|---------|
| `/synthea` | Generate Synthea modules and test data (multi-path) |
| `/umls` | Verify clinical codes via NIH UMLS MCP |
| `/phenotype_test_case` | Analyze algorithms, create per-path test cases, validate against FHIR |
| `/fhir_server_introspection` | Teach LLM to introspect server capabilities for Tier 2/3 eval |

### FHIR Query Agent (New — Standalone Package)

A user-facing, pip-installable package at `fhir-query-agent/` that packages our best agentic workflow for interactive use:

```bash
pip install -e fhir-query-agent/
fhir-query-agent --fhir-url http://localhost:8080/fhir --model qwen2.5:7b --umls-key YOUR_KEY
```

| Component | Description |
|-----------|-------------|
| `agent.py` | Model-agnostic agent loop with tool dispatch |
| `tools.py` | 5 tools (UMLS search, crosswalk, FHIR metadata, sample, search) |
| `prompts.py` | Optimized system prompt with workflow instructions |
| `adapters/ollama_adapter.py` | Ollama native tool calling |
| `adapters/anthropic_adapter.py` | Anthropic API (stub) |
| `cli.py` | Interactive CLI with `--fhir-url`, `--model`, `--umls-key` |
| `SKILL.md` | Claude Code skill definition |

### IG Profile Data

Format preference: **FSH > YAML > JSON** (FSH is most concise for LLM context windows).

| IG Version | Format | FSH Available | Condition.code Systems |
|------------|--------|:---:|----------------|
| **US Core 6.1.0** | JSON | Yes (via `goFSH`) | SNOMED + ICD-10-CM + **ICD-9-CM** |
| **US Core 8.0.1** | YAML | No (YAML readable) | SNOMED + ICD-10-CM (**ICD-9 removed**) |

Both downloaded to `data/ig-profiles/`.

### Test Data Summary

| Phenotype | Positive | Control | Total | Path Variety |
|-----------|:-------:|:------:|:-----:|:------------:|
| Type 2 Diabetes | 42 | 25 | 67 | 70% dx+meds, 30% meds-only |
| Asthma | 24 | 22 | 46 | 70% dx+meds, 30% meds-only |
| ADHD | 22 | 22 | 44 | 75% dx+meds, 25% meds-only |
| Atopic Dermatitis | 22 | 14 | 36 | 90% dx+meds, 10% meds-only |
| Atrial Fibrillation | 22 | 18 | 40 | 20% dx+meds, 80% meds-only |
| Autism | 22 | 22 | 44 | 60% dx+meds, 40% meds-only |
| AAA | 22 | 22 | 44 | 50% dx, 50% no-dx |
| ACE Inhibitor Cough | 22 | 22 | 44 | 50% dx+meds, 50% meds-only |
| AKI | 22 | 18 | 40 | 50% dx+labs, 50% labs-only |
| Appendicitis | 22 | 22 | 44 | 80% dx, 20% no-dx |
| Anxiety | 22 | 15 | 37 | 50% dx+meds, 50% meds-only |
| Sickle Cell Disease | 30 | * | 30+ | 50% dx+meds, 20% dx-only, 30% meds-only (Path C) |
| Hypothyroidism | 32 | 27 | 59 | 35% dx+labs+meds, 15% dx+meds, 30% meds-only, 20% labs-only |
| Dementia | 140 | 79 | 219 | 35% Path A, 25% Path B, 35% Path C (5 SNOMED subtypes + 5 RxNorm variants) |
| Depression | 35 | 27 | 62 | 35% dx+meds, 25% dx-only, 40% meds-only (Path C heavy) |
| Heart Failure | 50 | 30 | 80 | 35% Path A (dx+meds+EF), 15% Path B, 30% Path C (meds-only), 20% Path D (low EF only) |
| Rheumatoid Arthritis | 50 | 30 | 80 | 35% Path A (dx+meds+RF), 20% Path B, 30% Path C (DMARDs only), 15% Path D (RF only) |
| Chronic Kidney Disease | 50 | 30 | 80 | 30% Path A (dx+eGFR+UACR), 15% Path B, 35% Path C (eGFR only — undiagnosed CKD), 20% Path D (UACR + normal eGFR) |
| Breast Cancer | 50 | 30 | 80 | 60% Path A (dx+meds), 25% Path B (dx only), 15% Path C (chemoprevention — tamoxifen/AI without dx) |
| GERD | 50 | 30 | 80 | 35% Path A (dx+PPI), 15% Path B, 50% Path C (PPI only — flagship over-prescribing pattern) |
| Multiple Sclerosis | 50 | 30 | 80 | 60% Path A (dx+DMT), 30% Path B (dx only), 10% Path C (DMT only — small, MS DMTs are highly specific) |
| Hypertension | 50 | 30 | 80 | 35% Path A (dx+meds+high BP), 15% Path B, 25% Path C (antihypertensives for HF/CKD/edema), 25% Path D (silent/undiagnosed HTN) |
| Familial Hypercholesterolemia | 50 | 30 | 80 | 40% Path A (dx+statin+high LDL), 15% Path B, 15% Path C (statins for general CV risk), 30% Path D (UNDIAGNOSED FH — flagship) |
| Hepatitis C | 50 | 30 | 80 | 50% Path A (dx+DAA+Ab+), 25% Path B (dx+Ab+ untreated), 10% Path C (DAA only), 15% Path D (Ab+ resolved) |
| Type 1 Diabetes | 50 | 30 | 80 | 70% Path A (dx+insulin+HbA1c), 20% Path B (dx+insulin), 10% Path C (insulin without T1D dx) |
| HIV | 50 | 30 | 80 | 50% Path A (dx+ART+low CD4), 25% Path B (dx+ART), 10% Path C (ART only), 15% Path D (CD4 only) |
| Coronary Heart Disease | 50 | 30 | 80 | 50% Path A (dx+meds+procedure), 20% Path B (dx+meds), 15% Path C (meds only), 15% Path D (procedure only) |
| **Total** | **1121** | **715+** | **1836+** | |

Note: Synthea custom modules don't export Procedure FHIR resources reliably (need `duration` field + non-wellness encounters). Appendicitis and AAA procedure test cases affected.

## How to Run Evaluations

```bash
# 1. Start FHIR server
docker-compose up -d fhir-server

# 2. Install CLI
cd cli && pip install -e . && cd ..

# 3. Load ALL test data (infrastructure first, then patient bundles)
python run_batch_eval.py  # Loads automatically, or manually:
# for each phenotype: fhir-eval load synthea -p <phenotype>

# 4. Run single test case - Tier 1 (closed book)
fhir-eval run -t phekb-asthma-dx -p command -c "ollama run qwen2.5:7b" -v

# 5. Run single test case - Tier 2 (agentic with tools)
fhir-eval run -t phekb-asthma-dx -p ollama-agentic -m qwen2.5:7b -v

# 6. Run full batch comparison (all 34 test cases, both tiers)
python run_batch_eval.py --model qwen2.5:7b

# 7. Run with larger model
python run_batch_eval.py --model qwen3-coder:30b

# 8. Results saved to results/ directory
ls results/
```

### Interactive FHIR Query Agent

```bash
# Install the standalone agent
pip install -e fhir-query-agent/

# Interactive mode
fhir-query-agent --fhir-url http://localhost:8080/fhir --model qwen2.5:7b

# Single query
fhir-query-agent --fhir-url http://localhost:8080/fhir --model qwen2.5:7b \
  --query "Find all patients with asthma on inhaled corticosteroids"
```

## Remaining Work

### Immediate
1. **Re-run batch evaluation** with UMLS-powered agentic provider (should fix medication query failures)
2. **Implement three-layer evaluation decomposition** — replace single F1 with Layer 1 (resource type match), Layer 2 (code system accuracy), Layer 3 (execution F1). Layer 2 is our unique contribution — neither FHIRPath-QA nor FHIR-AgentBench evaluates clinical code resolution. See `docs/IMPLEMENTATION-ROADMAP.md`.
3. **VSAC integration** — add valueset access to UMLS MCP for Tier 3 evaluation
4. **Populate expected_patient_ids** — scan Synthea bundles to enable patient-level F1 scoring
5. **Add API credits** for Anthropic/Claude and OpenAI/GPT-4 evaluation

### Model Selection for Benchmarking
Choose models that enable direct comparison with published results. Decision pending — candidates:

| Model | Used By | Notes |
|-------|---------|-------|
| **o4-mini** | FHIRPath-QA (best base: 42%), FHIR-AgentBench (best agent: 50%) | Top priority — appears in both papers |
| **4o-mini** | FHIRPath-QA (SFT: 27%→79%) | Good SFT baseline reference |
| **Gemini-2.5-Flash** | FHIR-AgentBench (44% agent) | Strong open alternative |
| **Qwen3-32B** | FHIR-AgentBench (47% agent) | Ollama-compatible, no API cost |
| **LLaMA-3.3-70B** | FHIR-AgentBench (46% agent) | Ollama-compatible, no API cost |
| qwen2.5:7b | Our current baseline | Already tested (T1: 0.03, T2: 0.26) |
| qwen3-coder:30b | Planned | Larger local model |

### Tier 3 — Skill-Guided Evaluation
1. Integrate VSAC valueset access into UMLS MCP
2. Add `read_profile` and `read_valueset` tools for IG-aware queries
3. Create US Core variant Synthea modules (dual data sets)
4. Run 3-way comparison: Closed Book vs Tool-Assisted vs Skill-Guided

### Three-Layer Evaluation Implementation
1. **Layer 1 — Resource Type Match** (trivial): Parse resource type from generated query URL, compare against `expected_query.resource_type`. Binary metric.
2. **Layer 2 — Code System Accuracy** (our unique contribution):
   - 2a: Code system URI match (e.g., `http://snomed.info/sct` vs `http://hl7.org/fhir/sid/icd-10-cm`)
   - 2b: Code value match — strict (exact) or lenient (VSAC value set membership)
   - 2c: Code format correctness (`system|code` syntax)
   - Parse `code=` param from generated URL, compare against `metadata.required_codes[]`
   - **Key metric**: Tier 1→Tier 2 delta on Layer 2 quantifies UMLS/VSAC MCP server value
3. **Layer 3 — Execution Correctness** (already implemented): Existing precision/recall/F1 on patient IDs
4. **Reporting**: Update batch eval output to show per-layer breakdown, not just aggregate F1

### MIMIC-IV Evaluation Track (Track B)

MIMIC-IV on FHIR Demo (100 real patients) will serve as a **secondary evaluation track** alongside Synthea (Track A). Both FHIRPath-QA and FHIR-AgentBench use this dataset, enabling direct comparison with published results.

**Ground truth approach — Comprehensive Reference Queries:** For each phenotype, build a maximally inclusive FHIR query using VSAC-expanded value sets that cover all valid codes across all code systems (SNOMED, ICD-10-CM, ICD-9-CM). Execute this query to establish the reference patient set, then manually validate a sample. This addresses the open question of how to know the "right answer" without controlled synthetic data.

**Implementation steps:**
1. Download MIMIC-IV on FHIR Demo from PhysioNet
2. Load into HAPI FHIR (separate from Synthea data)
3. For 3-5 priority phenotypes (T2DM, AKI, asthma, atrial fibrillation):
   - Expand relevant VSAC value sets via `/umls expand <OID>`
   - Build comprehensive reference queries covering all code systems
   - Execute reference queries, collect patient sets
   - Manually validate a sample of results
   - Store in test case JSON as `mimic_test_data`
4. Run Tier 1/2/3 evaluations on both tracks

**Why this matters for our story:**
- **Synthea (Track A)**: Controlled ground truth. LLM must find the exact SNOMED code Synthea uses. Tests code specificity.
- **MIMIC (Track B)**: Real-world ground truth. LLM can use any valid code system. Tests clinical code breadth.
- On Synthea, an ICD-10 query scores L3=0 (SNOMED-only data). On MIMIC, the same ICD-10 query scores L3>0 (codes are present). The dual-track reveals whether failures are **data-mismatch** vs **genuinely wrong**.

See `docs/IMPLEMENTATION-ROADMAP.md` "Dual-Track Evaluation" for full specification.

### Framework Improvements
1. Build results comparison dashboard (web UI)
2. Add LLM judge evaluator (currently stubbed)
3. Support "acceptable alternative" queries (ICD-10 E11 valid even if SNOMED expected) — addressed by Layer 2 lenient mode
4. Track token usage and cost per evaluation
5. Expand to remaining 93 phenotypes

### FHIR Query Agent
1. Implement Anthropic adapter (Claude API tool use)
2. Add OpenAI adapter (function calling)
3. Add streaming output for interactive mode
4. Package as MCP server for use in Claude Desktop/other MCP clients
5. Publish to PyPI

## Resolved Issues

### Synthea T2D Module (Fixed 2026-03-12)
- Added `"wellness": true` on Encounter states
- Moved ConditionOnset inside encounters
- Upgraded to SCD-level RxNorm codes verified via UMLS
- Added multi-path generation: 70% diagnosed, 30% no-diagnosis (Path 4)

### FHIR Server Switch (Fixed 2026-03-12)
- Replaced fhir-candle with HAPI FHIR (stable in-memory, no healthcheck resets)
- Fixed bundle load order (infrastructure files first)

### Multi-Query Evaluation (Added 2026-03-12)
- Extended runner to detect `multi_query: true` test cases
- Added patient-level union evaluation
- Added query coverage scoring
- Added multi-query parser for LLM responses

### 10 Phenotype Expansion (Added 2026-03-15)
- Analyzed algorithms, verified codes via UMLS for 10 phenotypes
- Created 29 new multi-path test cases (dx, meds, labs, procedures, comprehensive)
- Created 20 new Synthea modules (positive + control for each)
- Generated and loaded 506 synthetic patients across 11 phenotypes
- Fixed Synthea Procedure export issue (requires `duration` field)
- Fixed AAA module: invalid SNOMED code 262684007 → 14336007, added `wellness: true`

### Hypothyroidism + Dementia + Depression Expansion (Added 2026-04-25)
- Analyzed PheKB algorithms, verified codes via UMLS + VSAC for 3 new phenotypes
- Created 14 new multi-path test cases:
  - Hypothyroidism: 6 cases (dx, meds, labs with TSH > 5 threshold, meds-only Path C, labs-only Path D, comprehensive)
  - Dementia: 4 cases including the flagship code-variation test with naive/broad/expert prompt levels
  - Depression: 4 cases with heavy Path C weighting (40%) for SSRI prescribing-without-dx pattern
- Created 6 new Synthea modules (positive + control × 3) all using the multi-path + code-variation pattern from SCD
- Generated 207 synthetic positive patients (32 hypo + 140 dementia + 35 depression) and 133 controls
- All 5 SNOMED subtype codes appeared in dementia data; all 6 RxNorm SCDs appeared in depression
- **Hypothyroidism uniquely exercises Path D** (abnormal labs only, untreated subclinical) — first phenotype with this tricky pattern
- **Dementia is the flagship code-variation test** — naive/broad/expert prompts isolate built-in code knowledge from clinical reasoning
- Loading + validation **completed 2026-04-25**: all 14 test cases have populated `expected_patient_ids` and `expected_result_count`
- Validation script: `scripts/validate_phenotype_test_cases.py` — runs each test case query against HAPI, maps HAPI patient IDs back to stable Synthea UUIDs, applies set-difference for `-meds-only` and `-labs-only` variants
- Final patient counts (post-validation):
  - Hypothyroidism: dx=11, meds=16, labs=12, meds-only=5 (Path C), labs-only=2 (Path D), comprehensive=18
  - Dementia: dx=23, meds=38, meds-only=22 (Path C), comprehensive=45
  - Depression: dx=12, meds=20, meds-only=13 (Path C — 52% of comprehensive), comprehensive=25
- Depression confirms the design intent — 13/25 = 52% of evidence-bearing patients are Path C (SSRI-without-dx), making the meds-only test the most diagnostic for this phenotype

### Heart Failure + Rheumatoid Arthritis + Chronic Kidney Disease Expansion (Added 2026-04-27)
- Analyzed PheKB algorithms (Mayo eMERGE HF V03042014, Harvard eMERGE RA 19Dec2017, Columbia CKD V4.2), verified codes via UMLS + VSAC for 3 new phenotypes covering different evaluation dimensions
- Created 15 new multi-path test cases (5 each):
  - **Heart Failure**: dx, meds (GDMT — furosemide, carvedilol, spironolactone, sacubitril/valsartan, empagliflozin), labs (EF<50% — first less-than threshold test case for HFrEF), meds-only Path C, comprehensive
  - **Rheumatoid Arthritis**: dx, meds (DMARDs + biologics — methotrexate, hydroxychloroquine, sulfasalazine, adalimumab, infliximab), labs (RF>14 IU/mL), meds-only Path C (cross-indication prescribing), comprehensive
  - **Chronic Kidney Disease**: dx, labs (eGFR<60), labs-only Path C (undiagnosed CKD by labs — most common pattern), albuminuria (UACR>30 — Path D), comprehensive
- Created 6 new Synthea modules (positive + control × 3) — all multi-path with code variation:
  - HF uses 5 SNOMED codes (parent HF, CHF, Chronic CHF, HFrEF 703272007, HFpEF 446221000) + 5 RxNorm GDMT ingredient codes
  - RA uses 5 SNOMED codes from VSAC OID 2.16.840.1.113883.3.464.1003.113.11.1081 + 5 DMARD/biologic ingredient codes
  - CKD uses 5 SNOMED stage codes (parent + stage 2/3/3A/4) — no medications (CKD has no phenotype-specific drug class)
- **Heart Failure introduces the lt-threshold pattern** — Observation?code=...&value-quantity=lt50 for EF — complementing prior gt-threshold tests (TSH, HbA1c, RF)
- **CKD has the heaviest Path C weighting (35%)** because real-world CKD is substantially undercoded — primary care often does not formally diagnose CKD even when eGFR < 60
- **CKD uniquely separates two lab-only paths**: Path C (low eGFR, no UACR — undiagnosed CKD) vs Path D (normal eGFR + elevated UACR — CKD Stage 1 by proteinuria, often missed even by lab-based screening)
- Generated 150 positive + 90 control patients (50/30 each) and loaded into HAPI (240 total)
- Loading + validation **completed 2026-04-27**: all 15 test cases have populated `expected_patient_ids` and `expected_result_count`. Final counts:
  - HF: dx=7, meds=12, labs=3, meds-only=5, comprehensive=13
  - RA: dx=19, meds=29, labs=3, meds-only=10, comprehensive=30
  - CKD: dx=6, labs=14, labs-only=8 (Path C dominant), albuminuria=4 (Path D), comprehensive=15
- CKD comprehensive (15) substantially exceeds dx-only (6) — confirms the design intent that lab-based screening reveals the dominant undiagnosed CKD population that Condition queries miss

### Breast Cancer + GERD + Multiple Sclerosis Expansion (Added 2026-04-27)
- Three new phenotypes covering the inverse-medication-specificity spectrum: **GERD has the most cross-prescribed drug class (PPIs)** while **MS has the most specific (DMTs)**, with **breast cancer** in the middle (chemoprevention adds small cross-use)
- Created 12 new multi-path test cases (4 each — no labs path for any of these phenotypes):
  - **Breast Cancer**: dx (5 SNOMED histologies — IDC, ILC, parent, generic carcinoma, invasive), meds (tamoxifen + 3 aromatase inhibitor SCDs + trastuzumab), meds-only Path C (chemoprevention), comprehensive
  - **GERD**: dx (3 SNOMED including findings used informally), meds (5 PPIs), meds-only Path C **flagship test** (PPI overprescribing), comprehensive
  - **Multiple Sclerosis**: dx (5 SNOMED including RRMS/SPMS/PPMS courses), meds (5 DMTs — natalizumab, alemtuzumab, ocrelizumab, dimethyl fumarate, fingolimod), meds-only Path C, comprehensive
- Created 6 new Synthea modules (positive + control × 3) — all 3-path with code variation
- Generated 150 positive + 90 control patients (50/30 each) and loaded into HAPI (cumulative 480 patients across 6 most-recent phenotypes)
- Loading + validation **completed 2026-04-27**: all 12 test cases populated. Final counts:
  - **Breast Cancer**: dx=21, meds=15, meds-only=2 (5% Path C — chemoprevention is rare), comp=23
  - **GERD**: dx=16, meds=31, meds-only=22 (**58% Path C — DOMINANT in entire suite**), comp=38
  - **Multiple Sclerosis**: dx=39, meds=31, meds-only=1 (3% Path C — DMTs are highly specific), comp=40
- **Path C inversion test confirmed**: GERD's PPI Path C dominates (58%) while MS's DMT Path C is near-zero (3%), demonstrating that medication-class specificity varies dramatically. This trio enables LLM evaluation of whether tools/reasoning correctly account for cross-indication prescribing.
- **GERD's 58% Path C is the largest in the suite** — even higher than Depression's 52% and CKD's labs-only ~50%. PPI overprescribing is the most diagnostic Path C signal we have.

### Hypertension + Familial Hypercholesterolemia + Hepatitis C Expansion (Added 2026-04-27 batch 3)
- Three more phenotypes filling distinct evaluation gaps:
  - **Hypertension** — first **vital-signs-driven** phenotype (Observation BP, not lab). Most common chronic disease. SBP>140 LOINC 8480-6.
  - **Familial Hypercholesterolemia** — first **genetic** phenotype. LDL≥190 mg/dL FH-specific cutoff (vs general 'high cholesterol' ≥130). Tests whether LLM knows FH-specific threshold.
  - **Hepatitis C** — first **infectious chronic disease**. HCV antibody screening + RNA confirmation (two-step diagnostic). DAAs are highly specific (low Path C like MS).
- Created 15 new multi-path test cases (5 each):
  - **HTN**: dx, meds (multi-class), **vitals (first BP-driven test)**, meds-only (cross-indication), comprehensive
  - **FH**: dx, meds (statins), labs (LDL≥190), labs-only (UNDIAGNOSED FH — flagship), comprehensive
  - **HCV**: dx, meds (DAAs), labs (HCV Ab), meds-only (rare), comprehensive
- Created 6 new Synthea modules (positive + control × 3) — all 4-path with code variation
- Generated 150 positive + 90 control patients (50/30 each) and loaded into HAPI
- Loading + validation **completed 2026-04-27**: all 15 test cases populated. Final counts:
  - **HTN**: dx=15, meds=27, vitals=5, meds-only=12, comp=28
  - **FH**: dx=17, meds=23, labs=4, labs-only=2 (UNDIAGNOSED FH cases — clinically valuable for genetic testing referral), comp=25
  - **HCV**: dx=21, meds=20, labs=10, meds-only=4, comp=27
- **HTN introduces vital-signs Observation testing** — the only phenotype using BP measurements instead of lab values. Tests LOINC 8480-6 with mm[Hg] units and category=vital-signs.
- **FH's flagship Path D test** (LDL≥190 + no FH dx + no statin) found 2 patients — the highest-yield population for genetic testing referral. The clinical importance of this test case far exceeds its small numeric count.
- **HCV introduces two-step diagnostic workup** — antibody screening (LOINC 13955-0) + RNA confirmation (LOINC 11011-4). Real-world HCV diagnosis requires both, unlike single-lab thresholds in other phenotypes.

### Type 1 Diabetes + HIV + Coronary Heart Disease Expansion (Added 2026-04-27 batch 4)
- Three more phenotypes filling distinct evaluation gaps:
  - **Type 1 Diabetes** — first **subtype-vs-subtype** test against an existing phenotype (T2D, already in suite). Tests whether LLM correctly distinguishes T1D SNOMED 46635009 from T2D SNOMED 44054006. Insulin-only therapy (no metformin) is the medication signature.
  - **HIV** — first **chronic infectious with suppressive treatment** (vs HCV's curative treatment). Modern combination tablet ARTs (Triumeq, Genvoya, Odefsey, Stribild, Complera). CD4 < 200 cells/μL defines AIDS.
  - **Coronary Heart Disease** — **FIRST working Procedure-resource test in the entire suite**. CABG, PCI, stent placement, and balloon angioplasty as Procedure resources (not Conditions or Medications). The CHD module proved the duration-field + non-wellness-Encounter pattern works.
- Created 12 new multi-path test cases (4 each):
  - **T1D**: dx (multi-subtype with subtype-vs-T2D distinction), meds (insulin-only), labs (HbA1c≥6.5), comprehensive
  - **HIV**: dx (HIV/AIDS/acute/detected), meds (5 modern combination tablet SCDs), labs (CD4<200), comprehensive
  - **CHD**: dx (extent-of-disease variants), meds (secondary prevention), **procedures (CABG/PCI/stent/balloon — flagship)**, comprehensive (FIRST multi-resource Patient query joining Condition + MedicationRequest + Procedure)
- Created 6 new Synthea modules (positive + control × 3) — CHD module includes the working Procedure pattern with `duration` field and ambulatory Encounter wrapping
- Generated 150 positive + 90 control patients (50/30 each) and loaded into HAPI (cumulative 960 patients)
- Loading + validation **completed 2026-04-27**: all 13 test cases populated. Final counts:
  - **T1D**: dx=38, meds=42, labs=7, comp=42
  - **HIV**: dx=31, meds=31, labs=7, comp=32
  - **CHD**: dx=13, meds=38, **procedures=7 (first successful Procedure resources)**, comp=40
- **CHD's procedure test (7 patients) is a milestone** — the first phenotype to successfully generate and query Procedure FHIR resources after prior issues with appendicitis/AAA. The pattern: non-wellness Encounter (encounter_class=ambulatory) wrapping a Procedure with `duration` field.
- **CHD's comprehensive test is the first multi-resource Patient query** unioning Condition + MedicationRequest + Procedure resources — testing whether LLM understands different FHIR resource types serve different clinical questions.
- **T1D's subtype-vs-T2D distinction** is novel — most phenotypes test multi-code variation within one disease; T1D tests whether LLM avoids the WRONG disease's codes (T2D codes would return 0 T1D patients).

### Venous Thromboembolism + Sleep Apnea + Crohn's Disease Expansion (Added 2026-04-27 batch 5)
- Three more phenotypes filling distinct evaluation gaps:
  - **Venous Thromboembolism (VTE)** — first **thrombotic disorder** in the suite. Tests anticoagulant Path C as classic cross-indication problem (warfarin/DOACs equally indicated for AFib, mechanical valves, post-op prophylaxis). D-dimer >0.5 mcg/mL FEU is the standard rule-out cutoff. Anatomic-extent code variation (DVT vs iliofemoral vs IVC) plus DVT-vs-PE distinction.
  - **Sleep Apnea** — first **sleep disorder** in the suite, and **second working Procedure-resource phenotype** (after CHD). Polysomnography (SNOMED 60554003) validates that the duration-field + non-wellness-Encounter pattern works beyond cardiac procedures. OSA-vs-CSA-vs-mixed mechanism distinction.
  - **Crohn's Disease** — first **IBD** in the suite. Tests IBD biologics (infliximab, adalimumab, ustekinumab) which have heavy cross-indication with RA/psoriasis/lupus. Mesalamine (5-ASA) is the most IBD-specific. Fecal calprotectin >250 mcg/g is the standard cutoff for active inflammation. Anatomic-location code variation (large bowel, terminal ileum, colon and rectum, jejunum and ileum).
- Created 12 new multi-path test cases:
  - **VTE**: dx (5 SNOMED anatomic + DVT/PE), meds (5 anticoagulants — warfarin + 3 DOACs + LMWH), labs (D-dimer>0.5), meds-only (TRICKY — anticoagulants without VTE dx), comprehensive
  - **Sleep Apnea**: dx (5 SNOMED OSA/CSA subtypes), procedures (polysomnography), comprehensive (Condition + Procedure union)
  - **Crohn's**: dx (5 SNOMED locations), meds (5-ASA + 3 biologics + immunomodulator), labs (calprotectin>250), comprehensive
- Created 6 new Synthea modules (positive + control × 3) — Sleep Apnea reuses the duration-field + ambulatory Encounter pattern proven in CHD
- Generated 226 positive + 96 control patients (72/82/72 + 32/32/32) and loaded into HAPI (cumulative 1270 patients)
- Loading + validation **completed 2026-04-27**: all 12 test cases populated. Final counts:
  - **VTE**: dx=29, meds=37, labs=7, meds-only=8, comp=37
  - **Sleep Apnea**: dx=36, procedures=4, comp=38
  - **Crohn's**: dx=28, meds=53, labs=3, comp=55
- **Sleep Apnea polysomnography (4 patients) confirms the Procedure pattern is reproducible** beyond cardiac contexts — the duration-field + non-wellness-Encounter approach now works for second resource type. Procedure yields are inherently low (~5-10% of generated patients export as Procedures), but reliably non-zero, which is sufficient for evaluating LLM resource-type selection.
- **VTE meds-only (8 patients) is a flagship Path C test** — these patients are on therapeutic anticoagulants without a VTE diagnosis, simulating the very real cross-indication problem (AFib stroke prevention, mechanical valves). LLMs that search only Condition resources will completely miss this population.
- **Crohn's biologic cross-indication is novel** — biologics like infliximab and adalimumab also appear in the RA module's medication list. A naive LLM querying anti-TNF biologics for "find Crohn's patients" will pick up RA patients. Resolution requires combining with Crohn's diagnosis or location-specific reasoning.

### Cross-Resource Test Cases via _has / _include / _revinclude (Added 2026-04-27)
- Five new test cases exercising FHIR's reverse-chain (`_has`), forward-chain (`_include`), and reverse-include (`_revinclude`) parameters. These test deeper FHIR query understanding beyond single-resource queries:
  - **`phekb-crohns-disease-biologic-disambig`**: `Patient?_has:Condition:patient:code=Crohn's&_has:MedicationRequest:patient:code=biologics` — solves the cross-indication problem (anti-TNFs are used in Crohn's AND RA). 15 patients (vs 28 with Crohn's dx alone, vs ~30 on biologics alone — the intersection is what matters).
  - **`phekb-type-2-diabetes-dx-and-uncontrolled`**: `Patient?_has:Condition:patient:code=T2D&_has:Observation:patient:code-value-quantity=4548-4$ge6.5` — combines diagnosis with abnormal lab using FHIR composite parameter (`code-value-quantity`) inside `_has`. HAPI supports this; many other servers do not. 14 patients.
  - **`phekb-coronary-heart-disease-dx-and-procedure`**: First `_has` test pairing Condition + Procedure resources. 5 patients (interventional-management CHD subset, distinct from medical-only).
  - **`phekb-crohns-disease-include-patient`**: `Condition?code=Crohn's&_include=Condition:patient` — forward chain pulls Patient resources alongside matched Conditions in one bundle (28 conditions + 28 patients = 56 entries).
  - **`phekb-coronary-heart-disease-revinclude-bundle`**: `Patient?_has:Condition:patient:code=CHD&_revinclude=Condition:patient&_revinclude=MedicationRequest:patient&_revinclude=Procedure:patient` — chart-review-style bundle assembly. 13 CHD patients + all their related resources.
- **Validation insights:**
  - HAPI fully supports `_has`, `_include`, `_revinclude`, AND the composite parameter `code-value-quantity` inside `_has`. The Crohn's biologic disambiguation result (15 patients) is strictly less than the union of Crohn's-dx (28) + biologic-Rx alone (~30), confirming the intersection works correctly.
  - These test cases stress LLM understanding of cross-resource semantics. A Tier 1 LLM that knows only single-resource FHIR queries will fail all five. A Tier 2 agentic LLM with introspection tools should be able to learn `_has`/`_include` from the CapabilityStatement.
  - The CHD interventional subset (5 patients) is significantly smaller than the dx population (13) — meaningful clinically, since patients without revascularization had medical management only. This single-query intersection cannot be done without `_has`.

### Adverse / Negation Test Cases (Added 2026-04-28)
- Four new test cases exercising the FHIR negation idiom — finding patients with one criterion but NOT another. FHIR R4 has no native `NOT EXISTS`, so the canonical solution is two-query subtraction (set A minus set B).
- Each test uses `multi_query: true` with a `negation: true` flag and a `negation_operation: "query[0]_patients - query[1]_patients"` directive in metadata, signaling client-side subtraction semantics.

| Test case | Pattern | Result | Clinical use |
|---|---|---|---|
| `phekb-venous-thromboembolism-anticoag-without-dx` | Anticoag Rx − VTE dx | 8 patients | AFib stroke prevention, mechanical valve, post-op prophylaxis |
| `phekb-crohns-disease-biologic-without-dx` | Biologic Rx − Crohn's dx | 19 patients | Mostly RA-on-biologic — pharmacovigilance |
| `phekb-type-1-diabetes-insulin-without-dx` | Insulin Rx − (T1D ∪ T2D) dx | 4 patients | Undocumented DM, steroid-induced hyperglycemia |
| `phekb-sleep-apnea-polysom-without-dx` | Polysom Procedure − OSA dx | 2 patients | Negative sleep studies — workup for other sleep disorders |

- **Key validation:** The biologic-without-Crohn's test (19 patients) confirms that **the RA module's anti-TNF biologics overlap with the Crohn's biologic set** — exactly the cross-indication contamination that the `phekb-crohns-disease-biologic-disambig` (intersection) test was designed to filter against. The 19-patient result of the negation pairs with the 15-patient result of the intersection: 34 total biologic patients = 15 with Crohn's dx + 19 without.
- **Multi-disease subtraction (insulin-without-DM)** demonstrates a more complex pattern: the subtracted set is a UNION of T1D + T2D codes, requiring the LLM to recognize that "diabetes" encompasses both subtypes for the negation. Result: 4 patients on insulin without ANY diabetes diagnosis.
- **Negative-study identification (polysomnography-without-OSA)** exercises Procedure-on-the-kept-side negation — different from the more common medication-without-diagnosis pattern.
- These 4 tests stress the LLM's ability to: (a) recognize that FHIR doesn't support `NOT EXISTS`, (b) decompose the negation into two queries, (c) compute set subtraction client-side. A Tier 1 LLM that returns only the medication query gets full union of the kept set (overcounts); a Tier 2 LLM that recognizes the negation and produces both queries gets full credit.

### Prostate Cancer + Epilepsy + PAD Expansion (Added 2026-04-28 batch 7)
- Three more phenotypes filling distinct evaluation gaps:
  - **Prostate Cancer** — **first sex-specific (male-only) phenotype** in the suite. Tests whether LLM produces correctly sex-restricted populations (no female patients in expected results). **Fourth Procedure-resource phenotype** (prostate biopsy). **Second 4-resource-type comprehensive query** (Condition + MedicationRequest + Procedure + Observation). PSA-based screening (LOINC 2857-1) at >4 ng/mL.
  - **Epilepsy** — first **seizure disorder** phenotype. **Fifth Procedure-resource phenotype** (EEG, the standard non-invasive diagnostic test). Multiple AED drug classes (sodium channel blockers, SV2A modulators, broad-spectrum); levetiracetam is the most prescribed modern AED.
  - **Peripheral Arterial Disease (PAD)** — first **peripheral vascular** phenotype, distinct from coronary CHD or venous VTE. Cilostazol is the PAD-specific PDE3 inhibitor for claudication; antiplatelets (aspirin, clopidogrel) and atorvastatin are heavily cross-indicated with other vascular phenotypes.
- Created 12 new multi-path test cases:
  - **Prostate Cancer**: dx (5 SNOMED stages), meds (5 ADT/anti-androgens — leuprolide/bicalutamide/enzalutamide/abiraterone/degarelix), labs (PSA>4), **procedures (biopsy)**, comprehensive (4-resource union, male-only)
  - **Epilepsy**: dx (5 SNOMED subtypes), meds (5 AEDs), **procedures (EEG)**, comprehensive
  - **PAD**: dx (5 SNOMED forms incl claudication), meds (cilostazol + pentoxifylline + cross-indicated antiplatelets/statin), comprehensive
- Created 6 new Synthea modules (positive + control × 3) — Prostate Cancer module includes a sex guard `gender: M`
- Generated 246 positive + 96 control patients (102/72/72 + 32/32/32) and loaded into HAPI (cumulative 1963 patients)
- Loading + validation **completed 2026-04-28**: all 12 test cases populated. Final counts:
  - **Prostate Cancer**: dx=6, meds=6, labs=3, procedures=2, comp=8
  - **Epilepsy**: dx=46, meds=46, procedures=9, comp=50
  - **PAD**: dx=24, meds=40 cross-indicated, comp=43
- **Procedure-resource pattern now confirmed across 5 distinct procedure types**: cardiac (CHD revascularization), sleep medicine (polysomnography), GI (colonoscopy), urologic biopsy (prostate), neurological (EEG). The duration-field + non-wellness-Encounter approach is reproducible across all procedural domains.
- **Sex-specificity demonstrated**: Prostate Cancer module uses a `Gender: M` guard — generated 102 male patients, 0 female patients. The expected_patient_ids therefore correctly contain only male patients, and an LLM that fails to handle sex-specific phenotypes (e.g., includes female anatomy queries) would over-recall on the FHIR data.
- **PAD cross-indication is the largest in the suite**: meds=40 vs dx=24, comprehensive=43. The 16-patient gap (meds without PAD dx) reflects that aspirin/clopidogrel/atorvastatin are shared with CHD, VTE, and FH modules. Cilostazol and pentoxifylline are PAD-specific markers — only ~7-8 patients in the meds set are actually PAD-only via these specific drugs.

### NAFLD + Cataracts + Severe Childhood Obesity Expansion (Added 2026-04-28 batch 9)
- Three more phenotypes filling distinct evaluation gaps:
  - **NAFLD (Non-Alcoholic Fatty Liver Disease)** — **first liver disease phenotype**. Tests metabolic liver pattern (ALT > AST inverted from alcoholic liver disease). Multi-stage diagnosis from steatosis → MASH/NASH → MASLD → cirrhosis. No medication path (lifestyle is the mainstay). Important addition since liver was a coverage gap.
  - **Cataracts** — first standalone **lens disorder** phenotype. **Ninth Procedure-resource phenotype** (cataract surgery — first **ophthalmologic-surgical** type, distinct from DR fundoscopy which was diagnostic-imaging). Multi-laterality codes (bilateral/unilateral) plus morphology (nuclear).
  - **Severe Early Childhood Obesity (SECO)** — **first pediatric phenotype** in suite. Age guard 5-17. BMI≥30 threshold (corresponds to ≥99th percentile in adolescents). Tests age-restricted population identification.
- Created 10 new multi-path test cases:
  - **NAFLD**: dx (5 SNOMED histologic stages), labs (ALT or AST >40 IU/L), comprehensive
  - **Cataracts**: dx (4 SNOMED laterality/morphology), procedures (cataract surgery), comprehensive
  - **SECO**: dx (5 SNOMED severity codes), labs (BMI≥30), comprehensive
- Created 6 new Synthea modules (positive + control × 3) — SECO module uses age range guard `>=5 AND <=17`, requires ~5x patient generation request to compensate for narrow age window.
- Generated 496 positive + 166 control patients (72/72/352 + 32/32/102) and loaded into HAPI (cumulative 3013 patients)
- Loading + validation **completed 2026-04-28**: all 10 test cases populated. Final counts:
  - **NAFLD**: dx=33, labs=8, comp=33
  - **Cataracts**: dx=15, procedures=6, comp=15
  - **SECO**: dx=263 (over-recalls — adult obesity patients also match these codes; pediatric restriction would need an explicit age filter on Patient resource), labs=37 (BMI≥30 measurements limited to pediatric ages), comp=273
- **SECO over-recall is a useful evaluation finding**: the dx-only query returns 263 (all obesity-coded patients including adults). The labs query (37) is age-restricted via the BMI Observation source, and the union (273) reflects adults+pediatric obesity. To return ONLY pediatric severe obesity, an LLM would need `Condition?code=...&patient.age=ge5&patient.age=le17` (FHIR doesn't directly support patient.age — requires birthdate calculation). This exposes a real LLM challenge for age-restricted phenotypes.
- **Procedure-resource pattern now confirmed across 9 procedural specialties**: cardiac (CHD revasc), sleep medicine (polysomnography), GI (colonoscopy), urologic (prostate biopsy), neurological (EEG), pulmonary imaging (chest X-ray), ophthalmologic-diagnostic (fundoscopy), gynecologic-surgical (oophorectomy/hysterectomy), and ophthalmologic-surgical (cataract surgery). Pattern is fully reproducible.

### Pneumonia + Diabetic Retinopathy + Ovarian Cancer Expansion (Added 2026-04-28 batch 8)
- Three more phenotypes filling distinct evaluation gaps:
  - **Pneumonia** — **first acute infection phenotype** (vs chronic HCV/HIV). Tests time-sensitive diagnosis-treatment-imaging pattern. **Sixth Procedure-resource phenotype** (chest X-ray — first diagnostic imaging procedure type). Antibiotics have **highest cross-indication contamination** in suite (shared with virtually all infectious indications).
  - **Diabetic Retinopathy** — **first diabetes complication phenotype**. Anti-VEGF intravitreal injections (ranibizumab, aflibercept, bevacizumab) — the most retinal-specific drug class. **Seventh Procedure-resource phenotype** (camera fundoscopy — first ophthalmologic procedure type).
  - **Ovarian Cancer** — **first female-specific (female-only) phenotype** (counterpart to male-only Prostate Cancer from batch 7). Sex guard `gender: F`. **Eighth Procedure-resource phenotype** (oophorectomy/hysterectomy — first gynecologic-surgical type). **Third 4-resource-type comprehensive query** (Condition + MedicationRequest + Procedure + Observation).
- Created 13 new multi-path test cases:
  - **Pneumonia**: dx (5 SNOMED etiologies — CAP, nosocomial, bacterial, viral), meds (5 antibiotics across classes), procedures (chest X-ray), comprehensive
  - **Diabetic Retinopathy**: dx (5 SNOMED severity codes incl. proliferative/nonproliferative/macular edema), meds (3 anti-VEGFs), procedures (fundoscopy), comprehensive
  - **Ovarian Cancer**: dx (5 SNOMED histologies), meds (5 chemo + PARP inhibitor), labs (CA-125>35), procedures (oophorectomy + hysterectomy), comprehensive (4-resource union, female-only)
- Created 6 new Synthea modules. Pneumonia + DR + Ovarian Cancer all generate Procedure resources with the duration-field + non-wellness-Encounter pattern. Ovarian Cancer module includes sex guard `gender: F` (request 2x to compensate).
- Generated 286 positive + 126 control patients (72/72/142 + 32/32/62) and loaded into HAPI (cumulative 2363 patients)
- Loading + validation **completed 2026-04-28**: all 13 test cases populated. Final counts:
  - **Pneumonia**: dx=37, meds=50, procedures=6, comp=50
  - **Diabetic Retinopathy**: dx=30, meds=21, procedures=13, comp=32
  - **Ovarian Cancer**: dx=26, meds=26, labs=8, procedures=6, comp=29
- **Procedure-resource pattern now confirmed across 8 distinct procedure types**: cardiac (CHD revasc), sleep medicine (polysomnography), GI (colonoscopy), urologic (prostate biopsy), neurological (EEG), pulmonary imaging (chest X-ray), ophthalmologic (fundoscopy), gynecologic-surgical (oophorectomy/hysterectomy). The duration-field + non-wellness-Encounter pattern is fully reproducible across all major procedural specialties.
- **Two sex-specific phenotypes now in suite**: Prostate Cancer (male-only, batch 7) + Ovarian Cancer (female-only, batch 8). Both use Synthea's `Gender` guard. The expected_patient_ids contain only the appropriate sex — an LLM that fails to handle sex-specificity will over-recall.
- **Pneumonia antibiotic cross-indication is the most aggressive in the suite**: meds=50 vs dx=37, comp=50. 13-patient gap reflects antibiotics from Crohn's biologic-induced infections, post-op prophylaxis, UTIs, etc. Diagnosis-only path is most specific for pneumonia identification.
- **DR meds path (21) significantly smaller than dx (30)**: anti-VEGF injections are reserved for proliferative/macular-edema cases — Path B (NPDR observation only, no anti-VEGF) drives this gap. Highly retinal-specific drug class with minimal cross-contamination.
- **Three 4-resource-type comprehensive queries now in suite**: CRC (batch 6), Prostate Cancer (batch 7), Ovarian Cancer (batch 8). These exercise the most complex multi-resource evaluation pattern.

### Harness — Negation-Aware Multi-Query Evaluator (Added 2026-04-28)
- **Problem**: The original `evaluate_multi_query_patient_union` always unioned patient results across queries. For negation tests where the LLM correctly produces `[keep_query, subtract_query]`, the union returned 37 patients (full anticoag set) instead of the expected 8 (anticoag minus VTE-diagnosed) — F1 ≈ 0.36 even though the LLM did the right thing.
- **Schema additions** (`backend/src/api/models/test_case.py`):
  - `metadata.negation: bool` (default False)
  - `metadata.negation_operation: Optional[str]` (e.g., `"query[0]_patients - query[1]_patients"`)
- **New evaluator method** (`backend/src/evaluation/execution.py`): `evaluate_multi_query_patient_difference(expected_patient_ids, generated_query_urls)` — runs query[0] as the keep set, unions query[1:] as the subtract set, returns set difference.
- **Runner dispatch** (`backend/src/evaluation/runner.py`): `_run_multi_query` now branches on `metadata.negation` — calls the difference evaluator for negation tests, union evaluator otherwise.
- **End-to-end results for `vte-anticoag-without-dx`**:
  - Correct LLM (both queries in order): F1 = **1.0** ✓
  - LLM forgot subtract query: F1 = 0.36 (precision penalty, recall preserved)
  - Old union path on same correct response: F1 = 0.36 (the regression we fixed)

### Harness — FHIR Client Pagination + Stable ID Resolution (Fixed 2026-04-28)
- **Two pre-existing bugs surfaced during negation testing**, both affecting all multi-query test cases:
  1. **No pagination**: `FHIRClient.get_patient_ids_from_query` only returned the first 20 patients (HAPI default page size). Now follows `Bundle.link[next]` and defaults to `_count=200`. Fix: `get_patient_ids_from_query` now accepts `page_size` and `max_pages` parameters.
  2. **HAPI internal IDs vs Synthea UUIDs**: fixtures store stable Synthea identifiers (so they survive HAPI re-loads), but the client returned raw HAPI IDs, causing 0% match. Added `_resolve_stable_patient_ids` that maps each HAPI ID → Synthea UUID via `Patient.identifier` (system `https://github.com/synthetichealth/synthea`), with a per-client cache to avoid repeated lookups. Default `resolve_stable_ids=True`.
- These two fixes were necessary prerequisites for negation evaluation to produce correct F1 scores.

### Harness — Code System Validation (Added 2026-04-28)
- **Replaced stub** that always returned `passed=False`. The harness now scores LLMs on whether they used the **correct vocabularies** (system URIs), independent of patient-level F1.
- **New module** (`backend/src/evaluation/code_validation.py`):
  - `extract_codes_from_url(url)` — parses any FHIR query URL into `(system, code)` tuples. Handles plain `code=`, chained `_has:Resource:patient:code=`, composite `code-value-quantity=...$ge6.5`, and comma-separated multi-code lists.
  - `_normalize_system(system)` — maps common LLM aliases (`SNOMED`, `RxNorm`, `ICD-10-CM`) to canonical FHIR URIs (`http://snomed.info/sct`, `http://www.nlm.nih.gov/research/umls/rxnorm`, etc.).
  - `CodeSystemValidator.evaluate(required_codes, urls)` — returns `CodeSystemValidationResult` with `correct_systems`, `incorrect_systems`, `missing_codes`, `extra_codes`, and `passed`.
- **Pass criteria**: all required systems used, no incorrect systems present, no codes missing a system URI. Missing individual codes are reported but don't fail the system-level check (that's already captured by execution F1).
- **Detects common LLM errors**: ICD-9 instead of ICD-10, missing system URI prefix (just bare codes), wrong vocabulary alias (e.g., calling RxNorm by its source-vocabulary name).
- **Updated overall_score weighting**:
  - Single-query: 50% execution F1 + 30% semantic + 20% code validation (was 60/40, no code dimension)
  - Multi-query: 60% execution F1 + 20% query coverage + 20% code validation (was 70/30)

### Colorectal Cancer + Migraine + SLE Expansion (Added 2026-04-28 batch 6)
- Three more phenotypes filling distinct evaluation gaps:
  - **Colorectal Cancer** — second cancer phenotype (after breast), and **third Procedure-resource phenotype** (colonoscopy) after CHD revascularization and Sleep Apnea polysomnography. **First test case unioning four FHIR resource types** (Condition + MedicationRequest + Procedure + Observation) in a single multi-query: CRC dx + chemo + colonoscopy + CEA. Tests anatomic-location code variation across colon/cecum/rectum.
  - **Migraine** — first **headache disorder** phenotype. Triptans (sumatriptan, rizatriptan, eletriptan, zolmitriptan, naratriptan) are highly migraine-specific — Path C cross-indication is essentially zero. Migraine has no defining laboratory marker, so no labs path.
  - **SLE (Systemic Lupus Erythematosus)** — first **systemic autoimmune** phenotype with multi-organ involvement. ANA antibody titer (LOINC 5048-4) at ≥1:160 as defining lab. Hydroxychloroquine is highly SLE-specific; methotrexate/azathioprine/MMF cross-indicated with RA, Crohn's, transplant.
- Created 13 new multi-path test cases:
  - **CRC**: dx (5 SNOMED anatomic), meds (FOLFOX/FOLFIRI 5-drug regimen), labs (CEA>5 ng/mL), **procedures (colonoscopy)**, comprehensive (4-resource-type union)
  - **Migraine**: dx (5 SNOMED subtypes incl aura/no-aura), meds (5 triptans), comprehensive (Condition + MedicationRequest)
  - **SLE**: dx (5 SNOMED organ-involvement variants), meds (5 immunomodulators), labs (ANA titer ≥160), comprehensive
- Created 6 new Synthea modules (positive + control × 3) — CRC reuses the duration-field + ambulatory Encounter Procedure pattern proven in CHD and Sleep Apnea
- Generated 216 positive + 96 control patients (72/72/72 + 32/32/32) and loaded into HAPI (cumulative ~1633 patients)
- Loading + validation **completed 2026-04-28**: all 13 test cases populated. Final counts:
  - **CRC**: dx=22, meds=22, labs=9, procedures=4, comp=27
  - **Migraine**: dx=43, meds=49, comp=57
  - **SLE**: dx=32, meds=68, labs=7, comp=70
- **CRC's 4-resource-type comprehensive test is a milestone** — first phenotype to require LLM to query Condition + MedicationRequest + Procedure + Observation in a single multi-query union. Tests whether LLM understands that different evidence types (diagnosis, treatment, screening procedure, surveillance lab) all belong to the same patient population.
- **Migraine's high triptan specificity** illustrates the cleanest "Path C is small" pattern in the suite — triptans alone are reliable migraine markers (49 patients on triptans, 43 with formal dx, comprehensive union 57 = ~14 with triptan-only or dx-only).
- **SLE's cross-indication contamination is the suite's largest** — meds=68 patients (vs dx=32) demonstrates that immunomodulators like azathioprine and methotrexate spread across our Crohn's, RA, and SLE Synthea modules. The biologic-disambiguation test case pattern from batch 5 (Crohn's `_has` intersection) is now applicable here too.

### Harness — Test Coverage (Added 2026-04-28)
- **51 backend tests, all passing**:
  - 5 unit tests for `evaluate_multi_query_patient_difference` (mock client)
  - 12 parametrized integration tests against live HAPI for the 4 adverse fixtures
  - 21 unit + fixture tests for `CodeSystemValidator` covering URL parsing, system normalization, missing/extra detection, multi-query aggregation
  - 13 unit + fixture tests for `PatientFilters` schema parsing and SECO age-restriction URL pattern
- Three scoring dimensions now covered: execution F1 (does it return the right patients?), semantic/coverage (does it target the right resource types?), code validation (does it use the correct vocabularies?).

### Harness — PatientFilters Schema + Age-Restriction Pattern (Added 2026-04-28)
- **Problem**: FHIR has no `Patient.age` search parameter. Pediatric phenotypes that share codes with adult populations (e.g., obesity SNOMED codes used by many Synthea modules) over-recall when queried by Condition alone. SECO `-dx` returned **263 patients** (adult+pediatric) when only ~50 were actually pediatric — a real LLM evaluation challenge documented in batch 9.
- **Schema additions** (`backend/src/api/models/test_case.py`):
  - New `PatientFilters` model with `min_age_years`, `max_age_years`, `sex`, and `reference_date` fields. `extra=allow` so future fields don't break older readers.
  - New `metadata.patient_filters: Optional[PatientFilters]` on `TestCaseMetadata`.
  - The `reference_date` is the anchor for age math — without a fixed date, age-restricted test cases drift over time.
- **URL pattern** for chained `Patient.birthdate` (HAPI confirmed working):
  - `min_age_years=5, max_age_years=17, reference_date=2026-04-28` →
  - `&patient.birthdate=gt2008-04-28&patient.birthdate=le2021-04-28`
  - Math: `birthdate > (ref - max_age - 1d)` AND `birthdate <= (ref - min_age)` — both inclusive at age boundaries when expressed this way.
  - HAPI evaluates the two clauses on the same query as AND.
- **End-to-end results for SECO** (refreshed via `scripts/validate_phenotype_test_cases.py`):
  - `phekb-severe-childhood-obesity-dx`: **263 → 42** (correct pediatric cohort)
  - `phekb-severe-childhood-obesity-comprehensive`: **273 → 52**
  - `phekb-severe-childhood-obesity-labs`: 37 → 37 (BMI Observations were already self-restricted; filter applied for consistency, idempotent)
- **Pattern generalizes**: any non-Patient resource, any age guard. Future age-restricted phenotypes (peanut allergy, neonatal opioid exposure) should use the same `PatientFilters` field and URL pattern.

### Agentic Evaluation Framework (Added 2026-03-15)
- Built `OllamaAgenticProvider` with native Ollama tool calling
- Implemented 5 tools: UMLS search, UMLS crosswalk, FHIR metadata, resource sample, FHIR search
- First batch evaluation: Tier 2 scored 9x better than Tier 1 (avg F1 0.265 vs 0.029)
- Identified medication query failure mode (ingredient vs SCD codes)
- Wired real UMLS API into agentic loop (replacing hardcoded lookup table)
- Auto-correction for MedicationOrder → MedicationRequest

### FHIR Query Agent Package (Added 2026-03-15)
- Created standalone `fhir-query-agent/` package
- Model-agnostic agent loop with Ollama adapter
- Interactive CLI for end-user FHIR query generation
- Claude Code skill definition

## File Map

| File | Status | Purpose |
|------|--------|---------|
| **Backend** | | |
| `backend/src/fhir/client.py` | Done | FHIR server client |
| `backend/src/llm/provider.py` | Updated | Multi-query parser, system prompt |
| `backend/src/llm/command_provider.py` | Updated | UTF-8 encoding fix, multi-query support |
| `backend/src/llm/agentic_provider.py` | **New** | Tier 2 agentic provider with UMLS + FHIR tools |
| `backend/src/llm/anthropic_provider.py` | Done | Anthropic SDK provider |
| `backend/src/evaluation/runner.py` | Updated | Multi-query detection, negation dispatch, code validation wired in |
| `backend/src/evaluation/execution.py` | Updated | Added `evaluate_multi_query_patient_difference` for negation tests |
| `backend/src/evaluation/code_validation.py` | **New** | `CodeSystemValidator` — URL parsing, system normalization, missing/extra detection |
| `backend/src/fhir/client.py` | Updated | Pagination + Synthea stable-ID resolution in `get_patient_ids_from_query` |
| `backend/src/api/models/evaluation.py` | Updated | Multi-query GeneratedQuery model |
| `backend/src/api/models/test_case.py` | Updated | Added `negation`/`negation_operation` and `PatientFilters` model with `patient_filters` field on TestCaseMetadata |
| `backend/tests/test_evaluation/test_execution_difference.py` | **New** | Unit tests for negation evaluator (5 tests) |
| `backend/tests/test_evaluation/test_negation_against_hapi.py` | **New** | Integration tests against live HAPI (12 tests) |
| `backend/tests/test_evaluation/test_code_validation.py` | **New** | URL parsing + validation logic tests (21 tests) |
| `backend/tests/test_api/test_patient_filters.py` | **New** | PatientFilters schema parsing + SECO fixture URL pattern tests (13 tests) |
| **CLI** | | |
| `cli/fhir_eval/commands/run.py` | Updated | Agentic provider support, tool trace display |
| `cli/fhir_eval/commands/load.py` | Updated | Loads infra files first |
| `run_batch_eval.py` | **New** | Batch evaluation runner (Tier 1 vs Tier 2) |
| **Synthea Modules** | | |
| `synthea/modules/custom/phekb_*.json` | 22 files | 11 phenotypes × (positive + control) |
| `synthea/generate_test_data.py` | Updated | Fixed Windows subprocess (gradlew.bat) |
| **Test Cases** | | |
| `test-cases/phekb/phekb-*-dx.json` | 11 files | Diagnosis code queries (easy) |
| `test-cases/phekb/phekb-*-meds.json` | 9 files | Medication queries (medium) |
| `test-cases/phekb/phekb-*-labs.json` | 2 files | Lab value queries (hard) |
| `test-cases/phekb/phekb-*-procedures.json` | 1 file | Procedure queries (medium) |
| `test-cases/phekb/phekb-*-comprehensive.json` | 11 files | Multi-query provider queries (expert) |
| `test-cases/phekb/phekb-*-path4*.json` | 1 file | Cross-resource queries (expert) |
| **FHIR Query Agent** | | |
| `fhir-query-agent/` | **New** | Standalone user-facing agent package |
| `fhir-query-agent/src/fhir_query_agent/agent.py` | New | Model-agnostic agent loop |
| `fhir-query-agent/src/fhir_query_agent/tools.py` | New | UMLS + FHIR tool implementations |
| `fhir-query-agent/src/fhir_query_agent/cli.py` | New | Interactive CLI |
| **Skills & Docs** | | |
| `.claude/skills/phenotype_test_case/SKILL.md` | Done | Algorithm analysis + test case methodology |
| `.claude/skills/synthea/SKILL.md` | Updated | Multi-path modules, GMF patterns |
| `.claude/skills/umls/SKILL.md` | Done | UMLS code lookup and crosswalk |
| `.claude/skills/fhir_server_introspection/SKILL.md` | Done | Server introspection for Tier 2/3 |
| `docs/PLAN-AGENTIC-EVALUATION.md` | Done | Full agentic evaluation architecture |
| `data/ig-profiles/us-core-8.0.1/` | Downloaded | US Core 8 profiles and valuesets |
| `docker-compose.yml` | Updated | HAPI FHIR + Azure FHIR |
