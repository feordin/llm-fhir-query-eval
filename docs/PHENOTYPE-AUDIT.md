# Phenotype Audit vs PheKB Raw Docs

Generated: comparing 108 modules in `synthea/modules/custom/` against `data/phekb-raw/`.

**Tier definitions:**
- **T1-significant-gap**: PheKB doc lists >=8 codes OR has lab thresholds OR has temporal logic. Module likely under-models the algorithm.
- **T2-minor-gap**: PheKB doc lists 3-7 codes. Module probably covers the basics but may miss some code variants.
- **T3-aligned**: PheKB doc has 0-2 codes (or matches module complexity).
- **T3-no-phekb**: No matching PheKB raw dir — clinical-knowledge-only phenotype.

## Tier counts

- **T1-significant-gap**: 63
- **T3-aligned**: 9
- **T3-no-phekb**: 36

## Phenotype-by-phenotype

| # | Phenotype | Tier | Module codes | Module paths | PheKB dir | PheKB codes | PheKB has labs/thresholds? | PheKB has temporal? |
|---|---|---|---|---|---|---|---|---|
| 1 | abdominal-aortic-aneurysm | T1-significant-gap | S:5 R:2 L:0 | 1p MP | abdominal-aortic-aneurysm-aaa | CPT:16, ICD-9-CM:11 | yes | yes |
| 2 | ace-inhibitor-cough | T1-significant-gap | S:2 R:5 L:0 | 2p M | ace-inhibitor-ace-i-induced-cough |  | no | no |
| 3 | acute-kidney-injury | T1-significant-gap | S:1 R:0 L:2 | 2p L | acute-kidney-injury-aki | LOINC:1 | yes | yes |
| 4 | adhd | T1-significant-gap | S:3 R:4 L:0 | 2p M | adhd-phenotype-algorithm | ICD-9-CM:38 | no | no |
| 5 | anxiety | T1-significant-gap | S:3 R:4 L:0 | 2p M | anxiety-algorithm |  | no | no |
| 6 | appendicitis | T1-significant-gap | S:4 R:0 L:0 | 1p P | appendicitis | ICD-9-CM:40, SNOMED CT:37, CPT:9 | no | no |
| 7 | asthma | T1-significant-gap | S:4 R:4 L:0 | 2p M | asthma | ICD-9-CM:37 | no | no |
| 8 | asthma-response-inhaled-steroids | T1-significant-gap | S:0 R:2 L:0 | 3p M | asthma-response-inhaled-steroids | ICD-9-CM:24 | no | no |
| 9 | atopic-dermatitis | T1-significant-gap | S:2 R:4 L:0 | 2p M | atopic-dermatitis-algorithm | ICD-9-CM:34 | yes | no |
| 10 | autism | T1-significant-gap | S:3 R:2 L:0 | 2p M | autism | ICD-9-CM:9 | no | no |
| 11 | autoimmune-disease | T1-significant-gap | S:0 R:0 L:0 | 1p | autoimmune-disease-phenotype | ICD-10-CM:1, SNOMED CT:1, ICD-9-CM:1 | no | yes |
| 12 | bone-scan-utilization | T1-significant-gap | S:1 R:0 L:0 | 1p P | bone-scan-utilization-0 | CPT:11, ICD-10-PCS:9, ICD-9-CM:2 | no | no |
| 13 | bph | T1-significant-gap | S:3 R:3 L:0 | 4p MP | phema-bph-benign-prostatic-hyperplasia-cases | ICD-9-CM:2, RxNorm:1, CPT:1 | no | no |
| 14 | breast-cancer | T1-significant-gap | S:5 R:5 L:0 | 3p M | breast-cancer | ICD-9-CM:1 | yes | no |
| 15 | ca-mrsa | T1-significant-gap | S:1 R:2 L:0 | 3p M | camrsa | ICD-9-CM:8 | no | yes |
| 16 | cardiorespiratory-fitness | T1-significant-gap | S:1 R:0 L:0 | 1p P | cardiorespiratory-fitness-algorithm-emerge-mayo-network-phenotype | ICD-9-CM:86, CPT:13 | yes | yes |
| 17 | carotid-atherosclerosis | T1-significant-gap | S:3 R:3 L:0 | 4p MP | caad-carotid-artery-atherosclerosis-disease | ICD-9-CM:4, CPT:1 | no | no |
| 18 | chronic-rhinosinusitis | T1-significant-gap | S:1 R:1 L:0 | 3p M | crs-chronic-rhinosinusitis | ICD-9-CM:2 | yes | no |
| 19 | ckd | T1-significant-gap | S:5 R:0 L:2 | 4p L | chronic-kidney-disease | CPT:1 | yes | yes |
| 20 | clopidogrel-poor-metabolizers | T1-significant-gap | S:1 R:1 L:0 | 3p M | clopidogrel-poor-metabolizers | CPT:24, ICD-9-CM:12 | yes | no |
| 21 | colorectal-cancer | T1-significant-gap | S:7 R:5 L:1 | 4p MLP | colorectal-cancer-crc | ICD-10-CM:63 | no | yes |
| 22 | coronary-heart-disease | T1-significant-gap | S:10 R:5 L:0 | 4p MP | coronary-heart-disease-chd | SNOMED CT:9, ICD-10-CM:7, CPT:5, ICD-9-CM:1 | no | no |
| 23 | crohns-disease | T1-significant-gap | S:5 R:5 L:1 | 4p ML | crohns-disease-demonstration-project | ICD-9-CM:55 | yes | no |
| 24 | dementia | T1-significant-gap | S:5 R:5 L:0 | 3p M | dementia | ICD-9-CM:23 | no | yes |
| 25 | depression | T1-significant-gap | S:5 R:6 L:0 | 3p M | depression | ICD-9-CM:1, ICD-10-CM:1 | no | no |
| 26 | developmental-language-disorder | T1-significant-gap | S:0 R:0 L:0 | 1p | developmental-language-disorder | ICD-10-CM:14, ICD-9-CM:8 | no | no |
| 27 | diabetic-retinopathy | T1-significant-gap | S:7 R:3 L:0 | 3p MP | diabetic-retinopathy |  | no | no |
| 28 | digital-rectal-exam | T1-significant-gap | S:1 R:0 L:0 | 1p P | digital-rectal-exam | ICD-10-PCS:9, CPT:6, ICD-9-CM:4, ICD-10-CM:1, SNOMED CT:1 | no | yes |
| 29 | diverticulitis | T1-significant-gap | S:1 R:2 L:0 | 3p M | diverticulosis-and-diverticulitis | CPT:58, ICD-9-CM:8, HICDA:4 | no | yes |
| 30 | drug-induced-liver-injury | T1-significant-gap | S:1 R:1 L:4 | 4p ML | drug-induced-liver-injury | ICD-9-CM:10, SNOMED CT:2 | yes | yes |
| 31 | epilepsy | T1-significant-gap | S:7 R:5 L:0 | 3p MP | epilepsyantiepileptic-drug-response-algorithm | ICD-10-CM:51, ICD-9-CM:46 | yes | no |
| 32 | familial-hypercholesterolemia | T1-significant-gap | S:5 R:5 L:1 | 4p ML | electronic-health-record-based-phenotyping-algorithm-familial-hypercholesterolemia | ICD-9-CM:40, ICD-10-CM:25, CPT:2, HCPCS:1 | no | no |
| 33 | functional-seizures | T1-significant-gap | S:1 R:0 L:0 | 1p | functional-seizures | ICD-9-CM:8, ICD-10-CM:6, CPT:2 | no | no |
| 34 | gerd | T1-significant-gap | S:3 R:5 L:0 | 3p M | gastroesophageal-reflux-disease-gerd-phenotype-algorithm | ICD-9-CM:34 | yes | no |
| 35 | heart-failure | T1-significant-gap | S:5 R:5 L:1 | 4p ML | heart-failure-hf-differentiation-between-preserved-and-reduced-ejection-fraction | ICD-9-CM:1, SNOMED CT:1 | yes | yes |
| 36 | herpes-zoster | T1-significant-gap | S:1 R:1 L:0 | 3p M | herpes-zoster |  | no | yes |
| 37 | hiv | T1-significant-gap | S:4 R:5 L:1 | 4p ML | hiv | LOINC:38 | no | no |
| 38 | hypertension | T1-significant-gap | S:5 R:5 L:1 | 4p ML | blood-pressure | ICD-10-CM:1 | no | no |
| 39 | intellectual-disability | T1-significant-gap | S:1 R:0 L:0 | 1p | intellectual-disability | ICD-10-CM:92, ICD-9-CM:42 | no | no |
| 40 | liver-cancer-staging | T1-significant-gap | S:2 R:0 L:4 | 1p LP | liver-cancer-staging-project |  | no | yes |
| 41 | lung-cancer | T1-significant-gap | S:3 R:0 L:0 | 1p | computable-phenotypes-identifying-patients-lung-and-gastroenteropancreatic-neuroendocrine | ICD-10-CM:30, ICD-9-CM:26 | no | no |
| 42 | migraine | T1-significant-gap | S:5 R:5 L:0 | 3p M | migraine | ICD-9-CM:25, ICD-10-CM:24 | yes | no |
| 43 | multimodal-analgesia | T1-significant-gap | S:1 R:3 L:0 | 3p MP | multimodal-analgesia | RxNorm:2 | no | no |
| 44 | multiple-sclerosis | T1-significant-gap | S:5 R:5 L:0 | 3p M | multiple-sclerosis-demonstration-project | ICD-9-CM:68 | no | no |
| 45 | nafld | T1-significant-gap | S:5 R:0 L:2 | 3p L | non-alcoholic-fatty-liver-disease-nalfd-alcoholic-fatty-liver-disease-ald | ICD-9-CM:14, ICD-10-CM:11, LOINC:4 | no | no |
| 46 | neonatal-abstinence-syndrome | T1-significant-gap | S:1 R:1 L:0 | 3p M | opioid-exposed-infants |  | yes | yes |
| 47 | ovarian-cancer | T1-significant-gap | S:8 R:5 L:1 | 4p MLP | ovarianuterine-cancer-ovutca | ICD-10-CM:5 | yes | yes |
| 48 | peanut-allergy | T1-significant-gap | S:1 R:1 L:1 | 3p ML | peanut-allergy | CPT:8 | no | no |
| 49 | peripheral-arterial-disease | T1-significant-gap | S:5 R:5 L:0 | 3p M | peripheral-arterial-disease-2012 | ICD-9-CM:23, CPT:18 | yes | no |
| 50 | pneumonia | T1-significant-gap | S:7 R:5 L:0 | 3p MP | pneumonia-vumc-emerge-v51 | RxNorm:1 | no | yes |
| 51 | post-event-pain | T1-significant-gap | S:1 R:0 L:1 | 1p LP | post-event-pain-algorithm | ICD-10-CM:38, ICD-9-CM:33, CPT:17, ICD-9-PROC:4 | yes | no |
| 52 | prostate-cancer | T1-significant-gap | S:7 R:5 L:1 | 4p MLP | prostate-cancer-0 |  | no | no |
| 53 | resistant-hypertension | T1-significant-gap | S:2 R:4 L:1 | 3p ML | resistant-hypertension | ICD-9-CM:34 | yes | yes |
| 54 | severe-childhood-obesity | T1-significant-gap | S:5 R:0 L:1 | 3p L | severe-early-childhood-obesity | ICD-9-CM:65 | yes | no |
| 55 | sickle-cell-disease | T1-significant-gap | S:3 R:1 L:0 | 3p M | sickle-cell-disease-0 | ICD-9-CM:10 | no | no |
| 56 | statins-and-mace | T1-significant-gap | S:2 R:1 L:1 | 3p ML | statins-and-mace | CPT:28, ICD-9-CM:3 | yes | yes |
| 57 | steroid-induced-avn | T1-significant-gap | S:1 R:1 L:0 | 3p M | steroid-induced-osteonecrosis | ICD-9-CM:49, CPT:40 | no | no |
| 58 | systemic-lupus-erythematosus | T1-significant-gap | S:5 R:5 L:1 | 4p ML | sle-systemic-lupus-erythematosus-using-slicc-systemic-lupus-internation-collaborating | ICD-10-CM:14, LOINC:11, ICD-9-CM:10, RxNorm:6, CPT:1 | no | yes |
| 59 | type-1-diabetes | T1-significant-gap | S:5 R:5 L:1 | 3p ML | type-1-and-type-2-diabetes-mellitus | RxNorm:33, LOINC:7, ICD-10-CM:2, ICD-9-CM:1 | yes | no |
| 60 | type-2-diabetes | T1-significant-gap | S:3 R:6 L:3 | 2p ML | type-2-diabetes-t2d | SNOMED CT:9, LOINC:9, ICD-9-CM:8, ICD-10-CM:7 | yes | no |
| 61 | urinary-incontinence | T1-significant-gap | S:1 R:3 L:0 | 3p M | urinary-incontinence | ICD-9-CM:1, ICD-10-CM:1, CPT:1 | yes | no |
| 62 | venous-thromboembolism | T1-significant-gap | S:5 R:5 L:1 | 4p ML | venous-thromboembolism-vte | ICD-9-CM:36 | no | no |
| 63 | warfarin-dose-response | T1-significant-gap | S:0 R:1 L:1 | 3p ML | warfarin-doseresponse |  | no | yes |
| 64 | atrial-fibrillation | T3-aligned | S:3 R:4 L:0 | 2p M | atrial-fibrillation-demonstration-project |  | no | no |
| 65 | cardiac-conduction-qrs | T3-aligned | S:1 R:0 L:0 | 1p P | cardiac-conduction-qrs |  | no | no |
| 66 | cataracts | T3-aligned | S:6 R:0 L:0 | 3p P | cataracts |  | no | no |
| 67 | clostridium-difficile | T3-aligned | S:1 R:1 L:0 | 3p M | clostridium-difficile-colitis |  | no | no |
| 68 | febrile-neutropenia-pediatric | T3-aligned | S:0 R:1 L:2 | 3p ML | febrile-neutropenia-pediatric |  | no | no |
| 69 | fibromyalgia | T3-aligned | S:1 R:3 L:0 | 3p M | identification-fibromyalgia-patients-rheumatoid-arthritis-cohort |  | no | no |
| 70 | hypothyroidism | T3-aligned | S:5 R:4 L:2 | 4p ML | hypothyroidism |  | no | no |
| 71 | rheumatoid-arthritis | T3-aligned | S:5 R:5 L:1 | 4p ML | rheumatoid-arthritis-demonstration-project |  | no | no |
| 72 | sleep-apnea | T3-aligned | S:7 R:0 L:0 | 3p P | sleep-apnea-phenotype |  | no | no |
| 73 | alcohol-use-disorder | T3-no-phekb | S:2 R:1 L:0 | 3p M | — | — | — | — |
| 74 | bipolar-disorder | T3-no-phekb | S:1 R:3 L:0 | 3p M | — | — | — | — |
| 75 | bladder-cancer | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 76 | cervical-cancer | T3-no-phekb | S:3 R:0 L:0 | 3p P | — | — | — | — |
| 77 | copd | T3-no-phekb | S:2 R:2 L:0 | 3p M | — | — | — | — |
| 78 | cystic-fibrosis | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 79 | down-syndrome | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 80 | endometriosis | T3-no-phekb | S:1 R:1 L:0 | 3p M | — | — | — | — |
| 81 | esophageal-cancer | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 82 | glaucoma | T3-no-phekb | S:3 R:1 L:0 | 3p M | — | — | — | — |
| 83 | glioblastoma | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 84 | gout | T3-no-phekb | S:1 R:2 L:1 | 4p ML | — | — | — | — |
| 85 | hearing-loss | T3-no-phekb | S:3 R:0 L:0 | 1p | — | — | — | — |
| 86 | hepatitis-c | T3-no-phekb | S:3 R:4 L:1 | 4p ML | — | — | — | — |
| 87 | hyperthyroidism | T3-no-phekb | S:2 R:1 L:1 | 3p ML | — | — | — | — |
| 88 | influenza | T3-no-phekb | S:1 R:1 L:0 | 3p M | — | — | — | — |
| 89 | iron-deficiency-anemia | T3-no-phekb | S:2 R:1 L:2 | 4p ML | — | — | — | — |
| 90 | leukemia | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 91 | liver-cancer | T3-no-phekb | S:3 R:0 L:1 | 3p L | — | — | — | — |
| 92 | lyme-disease | T3-no-phekb | S:1 R:1 L:0 | 3p M | — | — | — | — |
| 93 | lymphoma | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 94 | melanoma | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 95 | multiple-myeloma | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 96 | osteoporosis | T3-no-phekb | S:1 R:2 L:1 | 3p ML | — | — | — | — |
| 97 | pancreatic-cancer | T3-no-phekb | S:2 R:0 L:1 | 3p L | — | — | — | — |
| 98 | parkinsons-disease | T3-no-phekb | S:1 R:1 L:0 | 3p M | — | — | — | — |
| 99 | polycystic-kidney-disease | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 100 | psoriasis | T3-no-phekb | S:1 R:1 L:0 | 3p M | — | — | — | — |
| 101 | renal-cancer | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 102 | schizophrenia | T3-no-phekb | S:1 R:4 L:0 | 3p M | — | — | — | — |
| 103 | sepsis | T3-no-phekb | S:3 R:2 L:1 | 4p ML | — | — | — | — |
| 104 | stomach-cancer | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 105 | stroke | T3-no-phekb | S:2 R:3 L:0 | 3p M | — | — | — | — |
| 106 | thyroid-cancer | T3-no-phekb | S:1 R:0 L:0 | 1p | — | — | — | — |
| 107 | tuberculosis | T3-no-phekb | S:2 R:2 L:0 | 3p M | — | — | — | — |
| 108 | ulcerative-colitis | T3-no-phekb | S:1 R:1 L:0 | 3p M | — | — | — | — |

## T1 Significant-Gap Details

### abdominal-aortic-aneurysm

- PheKB dir: `data/phekb-raw/abdominal-aortic-aneurysm-aaa/`
- PheKB codes: {'CPT': 16, 'ICD-9-CM': 11}
- Module codes: SNOMED=['14336007', '185347001', '233985008', '24165007', '441788006'], RxNorm=['259255', '866514'], LOINC=[]
- PheKB files to read: ['AAA_Flowchart_v20120815.pdf', 'AAA_Flowchart_v20120815_1.pdf', 'Geisinger_AAA_Algorithm_Pseudocode_Final20120815_0.pdf', 'Geisinger_AAA_Algorithm_Pseudocode_Final20120815_0_1.pdf']
- Algorithm summary: The AAA phenotype algorithm classifies patients into three case types and controls. Case Type 1 requires AAA repair procedures (CPT codes 34800-35132). Case Type 2 requires ≥1 vascular clinic visit with ruptured AAA diagnosis (441.3). Case Type 3 requires ≥2 vascular clinic visits with unruptured AA...

### ace-inhibitor-cough

- PheKB dir: `data/phekb-raw/ace-inhibitor-ace-i-induced-cough/`
- PheKB codes: {}
- Module codes: SNOMED=['38341003', '49727002'], RxNorm=['198189', '314076', '314077', '858817', '898687'], LOINC=[]
- PheKB files to read: ['ACEi_cough_validation_guidelines_v3.doc']
- Algorithm summary: This phenotype identifies ACE inhibitor-induced cough cases and controls. Cases are defined as patients with documented cough as an allergy or adverse event associated with ACE inhibitor use. Controls are patients on ACE inhibitors for at least 6 months without documented cough adverse reactions and...

### acute-kidney-injury

- PheKB dir: `data/phekb-raw/acute-kidney-injury-aki/`
- PheKB codes: {'LOINC': 1}
- Module codes: SNOMED=['14669001'], RxNorm=[], LOINC=['2160-0', '3094-0']
- PheKB files to read: ['AKIalgorithm_V1.0.pdf']
- Algorithm summary: Rule-based AKI phenotype algorithm that follows KDIGO classification using serum creatinine changes. First excludes patients with pre-existing ESRD (kidney transplant or dialysis codes). Defines baseline SCr using hierarchical approach, then identifies AKI as ≥50% increase from baseline. Stages AKI ...

### adhd

- PheKB dir: `data/phekb-raw/adhd-phenotype-algorithm/`
- PheKB codes: {'ICD-9-CM': 38}
- Module codes: SNOMED=['192127007', '31177006', '406506008'], RxNorm=['1091392', '349594', '541892', '854834'], LOINC=[]
- PheKB files to read: ['ADHD20algorithm.docx']
- Algorithm summary: This ADHD phenotype algorithm identifies cases through two pathways: (1) age 4+ years with relevant ADHD ICD-9 codes (314.x series) in one or more visits on separate days PLUS ADHD medications, OR (2) age 4+ years with relevant ICD-9 codes in two or more visits on separate days. Cases are excluded i...

### anxiety

- PheKB dir: `data/phekb-raw/anxiety-algorithm/`
- PheKB codes: {}
- Module codes: SNOMED=['197480006', '21897009', '371631005'], RxNorm=['308048', '312941', '349332', '866083'], LOINC=[]
- PheKB files to read: ['Anxiety20Algorithm_0.docx']
- Algorithm summary: This anxiety phenotype algorithm identifies cases as individuals with 2+ anxiety-related ICD codes on different days after age 741 days, plus at least 1 relevant medication or therapy. Cases must have 365+ days of EHR history and be 741+ days old at last visit, with absence of exclusion codes. Contr...

### appendicitis

- PheKB dir: `data/phekb-raw/appendicitis/`
- PheKB codes: {'ICD-9-CM': 40, 'CPT': 9, 'SNOMED CT': 37}
- Module codes: SNOMED=['50849002', '74400008', '80146002', '85189001'], RxNorm=[], LOINC=[]
- PheKB files to read: ['appendicitis-algorithm-2016_5-5.pdf']
- Algorithm summary: The appendicitis phenotype algorithm identifies three case types: Case 1 uses pathology reports with SNOMED-CT concept unique identifiers (CUIs) requiring inflammation markers plus other pathological features; Case 2 identifies patients without pathology reports but with systemic antibiotic treatmen...

### asthma

- PheKB dir: `data/phekb-raw/asthma/`
- PheKB codes: {'ICD-9-CM': 37}
- Module codes: SNOMED=['195967001', '195977004', '233678006', '389145006'], RxNorm=['200224', '245314', '351109', '895994'], LOINC=[]
- PheKB files to read: ['Asthma20Phenotype20Algorithm_3.docx']
- Algorithm summary: The asthma phenotype algorithm identifies cases as individuals 4+ years old with both: (1) one or more asthma medication prescriptions AND (2) two or more asthma ICD9 codes (493.x) from separate in-person visits on different calendar days. Cases are excluded if they have any of the specified exclusi...

### asthma-response-inhaled-steroids

- PheKB dir: `data/phekb-raw/asthma-response-inhaled-steroids/`
- PheKB codes: {'ICD-9-CM': 24}
- Module codes: SNOMED=[], RxNorm=['19831', '41126'], LOINC=[]
- PheKB files to read: ['Asthma_ICS_Algorithm.docx']
- Algorithm summary: This phenotype identifies asthma patients aged 4-35 who respond to inhaled corticosteroids (ICS). It requires at least 2 asthma diagnoses (493.xx) on different days and excludes patients with various conditions like cystic fibrosis, immunodeficiency, COPD, and other respiratory/systemic diseases. Th...

### atopic-dermatitis

- PheKB dir: `data/phekb-raw/atopic-dermatitis-algorithm/`
- PheKB codes: {'ICD-9-CM': 34}
- Module codes: SNOMED=['24079001', '43116000'], RxNorm=['1014678', '1049630', '106258', '198145'], LOINC=[]
- PheKB files to read: ['Atopic20Dermatitis20Phenotype20Algorithm_0.docx']
- Algorithm summary: This atopic dermatitis phenotype algorithm identifies cases through two pathways: (1) individuals ≥60 days old with 2+ visits coded with ICD-9 691.8 plus 2+ prescriptions for AD-related medications, or (2) individuals ≥60 days old with 3+ visits coded with ICD-9 691.8. Cases are excluded if they hav...

### autism

- PheKB dir: `data/phekb-raw/autism/`
- PheKB codes: {'ICD-9-CM': 9}
- Module codes: SNOMED=['23560001', '35919005', '408856003'], RxNorm=['312804', '350386'], LOINC=[]
- PheKB files to read: ['Autism20glossary20of20terms.pdf', 'AutismAlgorithm_complete_v2.pdf']
- Algorithm summary: This autism phenotype algorithm uses a multi-step approach: 1) Include patients with autism spectrum disorder ICD-9 codes (299.0, 299.80, 299.9), 2) Exclude patients with specific conditions (299.1, 295*, 330.8, 759.5, 759.83), 3) Apply DSM-IV symptom criteria for three subtypes (Autistic Disorder, ...

### autoimmune-disease

- PheKB dir: `data/phekb-raw/autoimmune-disease-phenotype/`
- PheKB codes: {'ICD-10-CM': 1, 'SNOMED CT': 1, 'ICD-9-CM': 1}
- Module codes: SNOMED=[], RxNorm=[], LOINC=[]
- PheKB files to read: ['AutoimmuneDiseaseAlgorithm_V4_0.pdf', 'Validation20Instructions.docx']
- Algorithm summary: The autoimmune disease phenotype algorithm identifies cases and controls across 51 autoimmune diseases spanning 9 disease groups and 6 medical specialties. Cases are defined by having at least one autoimmune disease with 3 diagnosis codes on distinct days within the same disease, with first and last...

### bone-scan-utilization

- PheKB dir: `data/phekb-raw/bone-scan-utilization-0/`
- PheKB codes: {'CPT': 11, 'ICD-9-CM': 2, 'ICD-10-PCS': 9}
- Module codes: SNOMED=['41747008'], RxNorm=[], LOINC=[]
- PheKB files to read: ['BoneScan_phenotype.docx']
- Algorithm summary: This phenotype algorithm identifies bone scan utilization in prostate cancer patients by analyzing structured data (CPT/ICD procedure codes) and unstructured text (radiology reports and clinical notes). The cohort includes male patients 35+ years with prostate cancer diagnosis who have adequate enco...

### bph

- PheKB dir: `data/phekb-raw/phema-bph-benign-prostatic-hyperplasia-cases/`
- PheKB codes: {'ICD-9-CM': 2, 'RxNorm': 1, 'CPT': 1}
- Module codes: SNOMED=['266569009', '440655000', '90199006'], RxNorm=['25025', '37798', '77492'], LOINC=[]
- PheKB files to read: ['PhEMA_BPH_JAMIA_final_2018-06-13_draft_w_figures.pdf']
- Algorithm summary: The PhEMA BPH algorithm identifies cases of benign prostatic hyperplasia by selecting males age 40 and older who have no evidence of prostate, penile, urethral, or bladder cancer in their EHR. Cases are defined as those with BPH-related ICD-9 diagnostic codes on 2 separate days, plus at least one BP...

### breast-cancer

- PheKB dir: `data/phekb-raw/breast-cancer/`
- PheKB codes: {'ICD-9-CM': 1}
- Module codes: SNOMED=['254837009', '254838004', '278054005', '408643008', '713609000'], RxNorm=['10324', '199224', '200064', '224905', '310261'], LOINC=[]
- PheKB files to read: ['BreastCancerPhenotype_V2_71019.pdf']
- Algorithm summary: The algorithm identifies breast cancer cases and controls separated by sex using ICD-9/ICD-10 diagnostic codes, breast pathology reports, and medication lists. Female/male cases require either one occurrence of diagnostic codes OR two occurrences of history codes on distinct days. Controls are age-r...

### ca-mrsa

- PheKB dir: `data/phekb-raw/camrsa/`
- PheKB codes: {'ICD-9-CM': 8}
- Module codes: SNOMED=['423561003'], RxNorm=['190376', '2582'], LOINC=[]
- PheKB files to read: ['Phenotype20pseudocode20for20CA-MRSA_final_0.docx']
- Algorithm summary: This CA-MRSA phenotype algorithm identifies community-associated MRSA cases using two definitions: Gold standard requires culture-confirmed MRSA from outpatient/ED or within 72hrs of admission with SSTI site. Silver standard uses MRSA ICD-9 diagnosis codes with SSTI diagnosis within 7 days. Cases mu...

### cardiorespiratory-fitness

- PheKB dir: `data/phekb-raw/cardiorespiratory-fitness-algorithm-emerge-mayo-network-phenotype/`
- PheKB codes: {'CPT': 13, 'ICD-9-CM': 86}
- Module codes: SNOMED=['76746007'], RxNorm=[], LOINC=[]
- PheKB files to read: ['eMERGE_Cardiorespiratory_fitness_algorithm_8_12_2012.doc', 'eMERGE_CRF_Mayo_validation_summary_8_12_2012.doc', 'Meds_list_CRF_1_6_2013.doc']
- Algorithm summary: This algorithm identifies patients with cardiorespiratory fitness assessments by: 1) Excluding records with pharmacologic stress test codes, 2) Identifying cardiac exercise stress tests using combinations of ECG, Echo, nuclear test, and oxygen uptake CPT codes on the same date, 3) Flagging comorbid ...

### carotid-atherosclerosis

- PheKB dir: `data/phekb-raw/caad-carotid-artery-atherosclerosis-disease/`
- PheKB codes: {'ICD-9-CM': 4, 'CPT': 1}
- Module codes: SNOMED=['233259003', '440655000', '64586002'], RxNorm=['1191', '32968', '83367'], LOINC=[]
- PheKB files to read: ['CAAD_Network_Wide_Record_Counts_14Jan2014.docx', 'CAAD_NLP_User_Guide_v0.5_2015_02_11.docx', 'CAAD_Pseudo_Code_2014_12_29b.docx']
- Algorithm summary: The CAAD phenotype identifies carotid artery atherosclerosis disease cases and controls using both structured data and natural language processing. Cases are identified through ICD diagnosis codes (433.1*) and quantitative stenosis measurements extracted from imaging reports via NLP. The algorithm e...

### chronic-rhinosinusitis

- PheKB dir: `data/phekb-raw/crs-chronic-rhinosinusitis/`
- PheKB codes: {'ICD-9-CM': 2}
- Module codes: SNOMED=['40055000'], RxNorm=['108118'], LOINC=[]
- PheKB files to read: ['CRS2014AJRAHsuPacheco--SmithAvila-s16.pdf']
- Algorithm summary: The CRS phenotype algorithm uses a multi-step approach: 1) Initial case identification using ICD-9 codes 471.x (CRSwNP) and 473.x (CRS) plus CPT codes for sinus surgery, 2) Control identification by excluding patients with any CRS-related codes or sinus CT orders, 3) Algorithm refinement requiring C...

### ckd

- PheKB dir: `data/phekb-raw/chronic-kidney-disease/`
- PheKB codes: {'CPT': 1}
- Module codes: SNOMED=['431856006', '431857002', '433144002', '700378005', '709044004'], RxNorm=[], LOINC=['62238-1', '9318-7']
- PheKB files to read: ['CKDalgorithm_V4.2.pdf', 'CKDalgorithm_V4_validationInstruction_2.pdf', 'CKDalgorithm_V4_validationResults_2.docx']
- Algorithm summary: The CKD phenotype algorithm follows NKF KDOQI and KDIGO guidelines to identify and stage chronic kidney disease using EHR data. It uses two main measures: estimated glomerular filtration rate (eGFR) calculated with CKD-EPI equation for G-staging (Stages 1-5), and albuminuria for A-staging (A1-A3). T...

### clopidogrel-poor-metabolizers

- PheKB dir: `data/phekb-raw/clopidogrel-poor-metabolizers/`
- PheKB codes: {'CPT': 24, 'ICD-9-CM': 12}
- Module codes: SNOMED=['50849002'], RxNorm=['32968'], LOINC=[]
- PheKB files to read: ['ClopidogrelPhenotypeVESPA_100429_120yr20v6_0.docx', 'ClopidogrelPhenotypeVESPA_100429_220yr20v6_0.docx']
- Algorithm summary: This phenotype identifies clopidogrel poor metabolizers based on adverse cardiovascular events after clopidogrel use. Cases are defined as patients who experience MI, stroke, or need for revascularization following stent placement and clopidogrel therapy. The algorithm uses CPT codes to identify ste...

### colorectal-cancer

- PheKB dir: `data/phekb-raw/colorectal-cancer-crc/`
- PheKB codes: {'ICD-10-CM': 63}
- Module codes: SNOMED=['187760008', '363350007', '363406005', '440655000', '73761001', '93761005', '93771007'], RxNorm=['194000', '32592', '4492', '51499', '6313'], LOINC=['2039-6']
- PheKB files to read: ['GH_UW_CRC_ICD-10_Codes_2017_01_30.docx', 'GH_UW_CRC_Ptype_Pseudocode_2017_05_31.docx']
- Algorithm summary: This colorectal cancer phenotype uses a hierarchical 3-path approach: 1) First, identify cases through cancer registry data (highest priority), 2) Second, identify cases with CRC diagnosis codes plus surgical procedures within 365 days, 3) Third, identify cases with CRC diagnosis codes plus chemothe...

### coronary-heart-disease

- PheKB dir: `data/phekb-raw/coronary-heart-disease-chd/`
- PheKB codes: {'ICD-10-CM': 7, 'ICD-9-CM': 1, 'CPT': 5, 'SNOMED CT': 9}
- Module codes: SNOMED=['232717009', '233817007', '36969009', '371803003', '371804009', '414545008', '415070008', '440655000', '53741008', '68466008'], RxNorm=['1191', '20352', '32968', '36567', '83367'], LOINC=[]
- PheKB files to read: ['SmokingVariable.docx']
- Algorithm summary: The main coronary heart disease phenotype algorithm is based on eMERGE Network research where cases are ascertained by either two occurrences of diagnostic codes or one occurrence of a procedural code. Controls are defined as individuals with no diagnostic or procedural codes recorded. The smoking v...

### crohns-disease

- PheKB dir: `data/phekb-raw/crohns-disease-demonstration-project/`
- PheKB codes: {'ICD-9-CM': 55}
- Module codes: SNOMED=['1197732001', '1197733006', '196977009', '34000006', '7620006'], RxNorm=['1256', '191831', '327361', '52582', '847083'], LOINC=['38445-3']
- PheKB files to read: ['Demonstration20Project_phenotype20criteria_Crohns_08_04_07_clean.doc']
- Algorithm summary: This Crohn's disease phenotype algorithm classifies patients into cases, possible/probable cases, and controls. Cases require more than 2 occurrences of ICD-9 codes 555* (Regional enteritis) AND at least one specified medication. Two subcases are defined: 1) Crohn's with medications only (excluding ...

### dementia

- PheKB dir: `data/phekb-raw/dementia/`
- PheKB codes: {'ICD-9-CM': 23}
- Module codes: SNOMED=['230270009', '26929004', '312991009', '429998004', '52448006'], RxNorm=['1100184', '1599803', '310436', '996740', '997223'], LOINC=[]
- PheKB files to read: ['Dementia_EMR_definition_0.doc']
- Algorithm summary: The dementia phenotype algorithm identifies patients with presumptive Alzheimer's disease/dementia by selecting those who have either: (1) a minimum of 5 visits with any of the specified dementia ICD-9 diagnosis codes, OR (2) at least one fill of a dementia-specific medication. The algorithm uses a ...

### depression

- PheKB dir: `data/phekb-raw/depression/`
- PheKB codes: {'ICD-9-CM': 1, 'ICD-10-CM': 1}
- Module codes: SNOMED=['35489007', '36923009', '370143000', '66344007', '78667006'], RxNorm=['200371', '310385', '312938', '313580', '351250', '993537'], LOINC=[]
- PheKB files to read: ['Depression_Ptype_ver_2019_04_17.docx']
- Algorithm summary: The phenotype algorithm classifies patients into four mutually exclusive categories: likely cases, likely controls, potential cases, or potential controls. It uses the '2/30/180 rule' requiring depression evidence on at least 2 distinct days, 30-180 days apart. The algorithm analyzes four types of g...

### developmental-language-disorder

- PheKB dir: `data/phekb-raw/developmental-language-disorder/`
- PheKB codes: {'ICD-9-CM': 8, 'ICD-10-CM': 14}
- Module codes: SNOMED=[], RxNorm=[], LOINC=[]
- PheKB files to read: ['DLD20Manual20Chart20Review20rubric20from20Walters2C20Nitin20et20al20202020JSLHR.pdf', 'How20To20Use20APT-DLD_R_KNIME_July282020.pdf']
- Algorithm summary: APT-DLD is a two-step automated algorithm for identifying Developmental Language Disorder (DLD) cases in electronic health records. Step 1 (Broad Search) identifies pediatric patients with language disorder codes using 6 specific ICD-9/ICD-10 inclusion codes (315.39, 315.32, 315.31, F80.89, F80.2, F...

### diabetic-retinopathy

- PheKB dir: `data/phekb-raw/diabetic-retinopathy/`
- PheKB codes: {}
- Module codes: SNOMED=['1551000119108', '312912001', '314971001', '390834004', '440655000', '4855003', '59276001'], RxNorm=['1232150', '253337', '595060'], LOINC=[]
- PheKB files to read: ['DR-ChartReview-AbstractionForm.doc']
- Algorithm summary: This appears to be a manual chart review abstraction form for diabetic retinopathy phenotyping. The algorithm requires patients to have at least one diagnosis of diabetes as an inclusion criterion (exclusion if no diabetes). The form collects information about diabetes type (Type I/Juvenile, Type II...

### digital-rectal-exam

- PheKB dir: `data/phekb-raw/digital-rectal-exam/`
- PheKB codes: {'ICD-9-CM': 4, 'ICD-10-CM': 1, 'CPT': 6, 'ICD-10-PCS': 9, 'SNOMED CT': 1}
- Module codes: SNOMED=['410006001'], RxNorm=[], LOINC=[]
- PheKB files to read: ['DRE_Phenotype.pdf']
- Algorithm summary: The DRE phenotype algorithm identifies cases and controls from EHRs of male prostate cancer patients aged 35+. Cases are defined as patients with documented DRE performed within 6 months before first prostate cancer treatment, identified through physician notes and specific vocabulary terms. Control...

### diverticulitis

- PheKB dir: `data/phekb-raw/diverticulosis-and-diverticulitis/`
- PheKB codes: {'CPT': 58, 'ICD-9-CM': 8, 'HICDA': 4}
- Module codes: SNOMED=['307496006'], RxNorm=['2551', '6922'], LOINC=[]
- PheKB files to read: ['diverticulosis-flowchart_0.pdf', 'diverticulosis-flowchart_annotated.pdf', 'Diverticulosis-KNIME20instructions_3.pdf', 'diverticulosis-NLP-pipeline_2.pdf', 'Diverticulosis_and_Diverticulitis_overview.pdf', 'Marshfield20Diverticulosis20and20Diverticulitis20phenotype20Nov2014202012_0.docx']
- Algorithm summary: The phenotype algorithm identifies patients with diverticulosis and diverticulitis using two approaches: 1) Gold standard NLP approach analyzing colonoscopy reports for mentions of diverticulosis/diverticulitis with anatomical site detection, section filtering, and negation detection, 2) Alternative...

### drug-induced-liver-injury

- PheKB dir: `data/phekb-raw/drug-induced-liver-injury/`
- PheKB codes: {'ICD-9-CM': 10, 'SNOMED CT': 2}
- Module codes: SNOMED=['427399008'], RxNorm=['105585'], LOINC=['1742-6', '1920-8', '1975-2', '6768-6']
- PheKB files to read: ['DILIAlgorithm_merged_050813_0.pdf']
- Algorithm summary: The DILI phenotype algorithm identifies inpatients with acute drug-induced liver injury through a multi-step process: 1) Identifies patients with liver injury diagnosis (using ICD-9 codes or NLP) AND drug exposure within 3 months prior to diagnosis, 2) Confirms acute (not chronic) liver injury, 3) V...

### epilepsy

- PheKB dir: `data/phekb-raw/epilepsyantiepileptic-drug-response-algorithm/`
- PheKB codes: {'ICD-9-CM': 46, 'ICD-10-CM': 51}
- Module codes: SNOMED=['128613002', '19598007', '230456007', '313307000', '440655000', '54550000', '84757009'], RxNorm=['114477', '2002', '28439', '40254', '8183'], LOINC=[]
- PheKB files to read: ['Epilepsy20eMERGE20algorithm_1.docx']
- Algorithm summary: This is a two-part algorithm for identifying epilepsy cases and classifying drug response. Part 1 identifies epilepsy subjects using specific ICD-9/10 codes (345.x series and G40.x series) combined with antiepileptic drug prescriptions, while excluding cases with specific neurological conditions tha...

### familial-hypercholesterolemia

- PheKB dir: `data/phekb-raw/electronic-health-record-based-phenotyping-algorithm-familial-hypercholesterolemia/`
- PheKB codes: {'ICD-9-CM': 40, 'ICD-10-CM': 25, 'CPT': 2, 'HCPCS': 1}
- Module codes: SNOMED=['238078005', '238079002', '398036000', '403829002', '403830007'], RxNorm=['301542', '36567', '42463', '6472', '83367'], LOINC=['2089-1']
- PheKB files to read: ['Appendix_1_0.pdf', 'Appendix_2_0.pdf', 'FH_eAlgorithm_Flowcharts_2016_0.pdf', 'FH_eAlgorithm_Pseudocode_FullText_2016_1_3.pdf', 'FH_eAlgorithm_Pseudocode_FullText_2016_5.pdf', 'Map_ICD9_2_ICD10_CS_MSS_03222017_0.pdf', 'VALIDATION20OF20THE20FH20eALGORITHM20IN20THE20GEISINGER20HEALTH20SYSTEM_2017.pdf']
- Algorithm summary: Two-stage EHR-based phenotyping algorithm for Familial Hypercholesterolemia using modified Dutch Lipid Clinic Network (DLCN) criteria. Stage I identifies primary hypercholesterolemia cases/controls using structured laboratory data, medication history, and exclusion criteria for secondary causes. Sta...

### functional-seizures

- PheKB dir: `data/phekb-raw/functional-seizures/`
- PheKB codes: {'ICD-9-CM': 8, 'ICD-10-CM': 6, 'CPT': 2}
- Module codes: SNOMED=['191714002'], RxNorm=[], LOINC=[]
- PheKB files to read: ['FS_phenotyping_description_FINAL.docx']
- Algorithm summary: Two algorithms were developed to identify functional seizures (FS) patients. The primary algorithm identifies FS patients without concurrent epilepsy by requiring: (1) convulsion/conversion disorder ICD codes (300.11, 780.39, R56.9, or F44.5) AND (2) FS-related keywords ('pseudoseizure', 'psychogeni...

### gerd

- PheKB dir: `data/phekb-raw/gastroesophageal-reflux-disease-gerd-phenotype-algorithm/`
- PheKB codes: {'ICD-9-CM': 34}
- Module codes: SNOMED=['16331000', '235595009', '698065002'], RxNorm=['114979', '17128', '283742', '40790', '7646'], LOINC=[]
- PheKB files to read: ['GERD20chart20review20form.docx', 'GERD20phenotype20algorithm.docx']
- Algorithm summary: The GERD phenotype algorithm identifies cases through two pathways: (1) individuals ≥1,095 days old with 2+ GERD diagnosis codes (530.81 or 530.11) in separate visits PLUS 2+ GERD medication prescriptions, OR (2) individuals ≥1,095 days old with 3+ GERD diagnosis codes (530.81) in separate visits. C...

### heart-failure

- PheKB dir: `data/phekb-raw/heart-failure-hf-differentiation-between-preserved-and-reduced-ejection-fraction/`
- PheKB codes: {'ICD-9-CM': 1, 'SNOMED CT': 1}
- Module codes: SNOMED=['42343007', '446221000', '703272007', '84114007', '88805009'], RxNorm=['1545653', '1656339', '20352', '4603', '9997'], LOINC=['8806-2']
- PheKB files to read: ['Heart20Failure20Validation20Guidelines2011132013.docx', 'HF_algorithm_Cohort.pdf', 'Liu_CRI2013_0121_revised.pdf']
- Algorithm summary: This phenotype algorithm identifies heart failure cases from EHR data using a combination of ICD-9-CM diagnosis codes (428.X), natural language processing of clinical notes to identify HF terms (multi-organ failure, cardiac failure, CHF, heart failure, ventricular failure), and ejection fraction mea...

### herpes-zoster

- PheKB dir: `data/phekb-raw/herpes-zoster/`
- PheKB codes: {}
- Module codes: SNOMED=['4740000'], RxNorm=['281'], LOINC=[]
- PheKB files to read: ['Herpes_zoster_validation_guidelines_24Jan2013.docx']
- Algorithm summary: The phenotype algorithm identifies herpes zoster cases and controls based on clinical criteria rather than specific diagnostic codes. Cases are defined as individuals 40+ years old with a diagnosis of herpes zoster or varicella zoster since their 40th birthday, with at least 5 years of healthcare sy...

### hiv

- PheKB dir: `data/phekb-raw/hiv/`
- PheKB codes: {'LOINC': 38}
- Module codes: SNOMED=['111880001', '165816005', '62479008', '86406008'], RxNorm=['1147334', '1306292', '1546888', '1721613', '1741733'], LOINC=['24467-3']
- PheKB files to read: ['Phenotyping_Algorithm_HIV1_2.docx']
- Algorithm summary: The HIV phenotyping algorithm identifies patients aged 13 or older with HIV through inclusion criteria: (1) positive HIV confirmatory test results, (2) HIV viral load >1000 copies/mL, or (3) prescription for HIV-specific antiretroviral medications. Exclusion criteria remove patients under 13 years o...

### hypertension

- PheKB dir: `data/phekb-raw/blood-pressure/`
- PheKB codes: {'ICD-10-CM': 1}
- Module codes: SNOMED=['1201005', '371125006', '429457004', '59621000', '78975002'], RxNorm=['17767', '20352', '29046', '4603', '52175'], LOINC=['8480-6']
- PheKB files to read: ['Blood20pressure.docx']
- Algorithm summary: Multi-step blood pressure phenotype algorithm: 1) Extract SBP/DBP measurements using codes from CSV files (SBP_codes.csv, SBP_LOINC_codes.csv, DBP_codes.csv, DBP_LOINC_codes.csv), 2) Convert units to mm Hg, 3) Apply exclusions (age <18, inpatient/ED visits, end stage kidney disease, pregnancy), 4) A...

### intellectual-disability

- PheKB dir: `data/phekb-raw/intellectual-disability/`
- PheKB codes: {'ICD-9-CM': 42, 'ICD-10-CM': 92}
- Module codes: SNOMED=['110359009'], RxNorm=[], LOINC=[]
- PheKB files to read: ['Intellectual20disability20Algorithm.docx']
- Algorithm summary: This phenotype algorithm identifies cases of intellectual disability by requiring patients to be at least 731 days old with two or more relevant intellectual disability diagnosis codes (ICD-9: 317, 318.0-318.2, 319; ICD-10: F70-F73, F78-F79, R41.83) documented in two or more in-person visits. Cases ...

### liver-cancer-staging

- PheKB dir: `data/phekb-raw/liver-cancer-staging-project/`
- PheKB codes: {}
- Module codes: SNOMED=['169070004', '25370001'], RxNorm=[], LOINC=['1751-7', '1834-1', '1975-2', '6301-6']
- PheKB files to read: ['annotation_examples.pdf', 'clinical_notes_section_ontology.docx']
- Algorithm summary: This phenotype algorithm identifies hepatocellular carcinoma (HCC) liver cancer stages using three staging systems: AJCC (stages I, II, IIIa, IIIb, IIIc, IVa, IVb), BCLC (stages A1, A2, A3, A4, B, C, D), and CLIP (stages 0-6). Step 1 involves collecting patient files from a single day to isolate ons...

### lung-cancer

- PheKB dir: `data/phekb-raw/computable-phenotypes-identifying-patients-lung-and-gastroenteropancreatic-neuroendocrine/`
- PheKB codes: {'ICD-9-CM': 26, 'ICD-10-CM': 30}
- Module codes: SNOMED=['254632001', '254637007', '363358000'], RxNorm=[], LOINC=[]
- PheKB files to read: ['lung_gep_nets.pdf']
- Algorithm summary: The phenotype uses multiple approaches: 1) High PPV phenotype for low-touch recruitment requiring at least 2 NET codes >30 days apart with first code after 01JAN2018, achieving 90-98% PPV for GEP NETs and 92% PPV for lung NETs; 2) High sensitivity phenotype for first-pass identification when chart r...

### migraine

- PheKB dir: `data/phekb-raw/migraine/`
- PheKB codes: {'ICD-9-CM': 25, 'ICD-10-CM': 24}
- Module codes: SNOMED=['230461009', '37796009', '4473006', '56097005', '59292006'], RxNorm=['135775', '141366', '231049', '37418', '88014'], LOINC=[]
- PheKB files to read: ['Migraine_10202017.docx']
- Algorithm summary: The migraine phenotype algorithm classifies patients into four main categories: hemiplegic migraine, migraine with aura, migraine without aura, and unclassified migraine. It uses specific ICD-9 and ICD-10 codes with frequency thresholds (≥4 encounters for without aura, ≥1 for with aura, ≥2 for uncla...

### multimodal-analgesia

- PheKB dir: `data/phekb-raw/multimodal-analgesia/`
- PheKB codes: {'RxNorm': 2}
- Module codes: SNOMED=['387713003'], RxNorm=['161', '5640', '7804'], LOINC=[]
- PheKB files to read: ['Multimodal20Analgesia.pdf']
- Algorithm summary: This phenotype identifies surgical patients receiving multimodal analgesia (combination of opioids with NSAIDs and/or acetaminophen) at discharge. Cases are defined as patients with: 1) ICD-9/ICD-10 surgical procedure codes, 2) documented multimodal regimen use postoperatively, 3) documentation in E...

### multiple-sclerosis

- PheKB dir: `data/phekb-raw/multiple-sclerosis-demonstration-project/`
- PheKB codes: {'ICD-9-CM': 68}
- Module codes: SNOMED=['192927008', '24700007', '425500002', '426373005', '428700003'], RxNorm=['1012896', '117055', '1373478', '1876366', '354770'], LOINC=[]
- PheKB files to read: ['Demonstration20Project_phenotype20criteria_MS_08_03_21.doc', 'MS_2010_Aug205_0.docx']
- Algorithm summary: The Multiple Sclerosis phenotype algorithm identifies definitive cases through two pathways: Type 1 requires two or more ICD-9 code 340 (MS), while Type 2 requires specific demyelinating disease codes (341.9, 323.9, 341.2) AND MS-specific medications (Avonex, Betaseron, Copaxone, Tysabri) with prope...

### nafld

- PheKB dir: `data/phekb-raw/non-alcoholic-fatty-liver-disease-nalfd-alcoholic-fatty-liver-disease-ald/`
- PheKB codes: {'ICD-9-CM': 14, 'ICD-10-CM': 11, 'LOINC': 4}
- Module codes: SNOMED=['197321007', '19943007', '442191002', '442685003', '722866000'], RxNorm=[], LOINC=['1742-6', '1920-8']
- PheKB files to read: ['NAFLD-inclusion-exclusion_final_06182018.docx']
- Algorithm summary: The phenotype algorithm defines two main cases: NAFLD (Cases 1 & 2) and ALD (Case 3). NAFLD cases require inclusion ICD-9 codes (571.5, 571.8, 571.9) or ICD-10 codes (K75.81, K76.0, K76.9), evidence of hepatic steatosis by imaging/histology or clinical notes with diagnostic text, and exclusion of pa...

### neonatal-abstinence-syndrome

- PheKB dir: `data/phekb-raw/opioid-exposed-infants/`
- PheKB codes: {}
- Module codes: SNOMED=['414819007'], RxNorm=['7052'], LOINC=[]
- PheKB files to read: ['Opioid20Exposed20Infants20Phenotype20Algorithm.docx']
- Algorithm summary: The phenotype algorithm identifies opioid-exposed infants using a population of birthing person-infant dyads from 2010-2022. Population criteria include: evidence of live birth, infant >=33 weeks gestation, and exclusion of critical illness/respiratory procedures and major congenital malformations. ...

### ovarian-cancer

- PheKB dir: `data/phekb-raw/ovarianuterine-cancer-ovutca/`
- PheKB codes: {'ICD-10-CM': 5}
- Module codes: SNOMED=['123843001', '236886002', '254850005', '254852002', '363443007', '440655000', '83152002', '93934004'], RxNorm=['12574', '1597582', '2555', '40048', '56946'], LOINC=['10334-1']
- PheKB files to read: ['OV_CA_Pseudo_Code_2018_06_07.docx', 'OV_UT_CA_Network_Wide_Record_Counts_2018_02_12.docx']
- Algorithm summary: This phenotype identifies ovarian/uterine cancer cases using a multi-step process: 1) Subject must be female, 2) Must have qualifying cancer diagnosis codes (ovarian, uterine, peritoneal, fallopian, or endometrial) that satisfy a '2/30 rule' (same specific code appearing at least twice over ≥30 days...

### peanut-allergy

- PheKB dir: `data/phekb-raw/peanut-allergy/`
- PheKB codes: {'CPT': 8}
- Module codes: SNOMED=['91935009'], RxNorm=['1660014'], LOINC=['6206-7']
- PheKB files to read: ['Peanut_Allergy_algorithm_0.pdf']
- Algorithm summary: The peanut allergy phenotype algorithm identifies patients from a searchable database with any mention of 'peanut' in their EMR. It then classifies them into two case types: Case Type 1 includes patients with quantitative immunoassay testing (RAST) or CPT code 86003 for allergen-specific IgE testing...

### peripheral-arterial-disease

- PheKB dir: `data/phekb-raw/peripheral-arterial-disease-2012/`
- PheKB codes: {'CPT': 18, 'ICD-9-CM': 23}
- Module codes: SNOMED=['314902007', '399957001', '400047006', '421895002', '63491006'], RxNorm=['1191', '21107', '32968', '8013', '83367'], LOINC=[]
- PheKB files to read: ['Mayo_PAD_algo_billing_codes_april_2010.doc', 'Mayo_PAD_phenotype_algorithm_final.doc']
- Algorithm summary: The PAD phenotype algorithm uses a multi-tiered approach: 1) Gold standard based on vascular lab ABI measurements (ABI ≤0.90 or poorly compressible arteries with ABI >1.4 or ankle BP >255mmHg), 2) ICD-9-CM diagnosis codes for PAD (440.2x, 440.3x, 440.8x), 3) Procedure codes for lower extremity inter...

### pneumonia

- PheKB dir: `data/phekb-raw/pneumonia-vumc-emerge-v51/`
- PheKB codes: {'RxNorm': 1}
- Module codes: SNOMED=['233604007', '385093006', '399208008', '425464007', '440655000', '53084003', '75570004'], RxNorm=['18631', '2193', '3640', '723', '82122'], LOINC=[]
- PheKB files to read: ['PNAemergeVUMCv51.pdf']
- Algorithm summary: This phenotype algorithm identifies bacterial pneumonia cases by combining three main criteria: (1) non-negated radiology reports mentioning 'pneumonia' using natural language processing, (2) at least 2 ICD9/10 pneumonia diagnosis codes within a 62-day window around the radiology event, and (3) at l...

### post-event-pain

- PheKB dir: `data/phekb-raw/post-event-pain-algorithm/`
- PheKB codes: {'ICD-9-CM': 33, 'ICD-10-CM': 38, 'CPT': 17, 'ICD-9-PROC': 4}
- Module codes: SNOMED=['387713003'], RxNorm=[], LOINC=['38208-5']
- PheKB files to read: ['Post-pain_071318.docx']
- Algorithm summary: This phenotype algorithm identifies post-event pain in two distinct populations: (1) Pediatric patients ≥6 years old undergoing scoliosis or pectus excavatum surgery with specific CPT/ICD procedure codes, requiring ≥3 NRS pain scores per encounter, and (2) African American individuals with sickle ce...

### prostate-cancer

- PheKB dir: `data/phekb-raw/prostate-cancer-0/`
- PheKB codes: {}
- Module codes: SNOMED=['126906006', '369485004', '399068003', '440655000', '65575008', '93974005', '94503003'], RxNorm=['1100072', '1307298', '42375', '475230', '83008'], LOINC=['2857-1']
- PheKB files to read: ['Prostate20Cancer.pdf']
- Algorithm summary: This prostate cancer phenotype algorithm defines cases as males aged 18+ with at least two occurrences of malignant neoplasm of prostate codes on different dates. Controls are males with no malignant prostate neoplasm codes, no non-malignant prostate neoplasm codes, no prostatectomy codes, and at le...

### resistant-hypertension

- PheKB dir: `data/phekb-raw/resistant-hypertension/`
- PheKB codes: {'ICD-9-CM': 34}
- Module codes: SNOMED=['38341003', '461301000124109'], RxNorm=['17767', '29046', '5487', '9997'], LOINC=['8480-6']
- PheKB files to read: ['Algorithm20for20Resistant20Hypertension202010-06_21.doc']
- Algorithm summary: This algorithm identifies resistant hypertension cases through two types: Type 1 requires ≥4 simultaneous antihypertensive medication classes on ≥2 occasions (1 month apart); Type 2 requires 3 simultaneous medication classes plus elevated BP measurements (SBP >140 or DBP >90) at least one month afte...

### severe-childhood-obesity

- PheKB dir: `data/phekb-raw/severe-early-childhood-obesity/`
- PheKB codes: {'ICD-9-CM': 65}
- Module codes: SNOMED=['238136002', '408512008', '414915002', '414916001', '443381000124105'], RxNorm=[], LOINC=['39156-5']
- PheKB files to read: ['ObesityAlgorithm_complete_final_rev022414.pdf']
- Algorithm summary: This phenotype algorithm identifies severe early childhood obesity cases and controls in children aged 1-6 years. Cases require multiple BMI measurements with >= 99th percentile readings and >50% of measurements >76th percentile. Controls require BMI measurements between 5th-85th percentiles in chil...

### sickle-cell-disease

- PheKB dir: `data/phekb-raw/sickle-cell-disease-0/`
- PheKB codes: {'ICD-9-CM': 10}
- Module codes: SNOMED=['127040003', '35434009', '36472007'], RxNorm=['5552'], LOINC=[]
- PheKB files to read: ['Computable20Phenotype20Description.pdf']
- Algorithm summary: The phenotype identifies patients with sickle cell disease using a two-step process: 1) Presence of qualifying ICD-9 codes for sickle cell disease (282.41, 282.42, 282.60, 282.61, 282.62, 282.63, 282.64, 282.68, 282.69) in problem list, encounter diagnosis, or discharge diagnosis, AND 2) Evidence of...

### statins-and-mace

- PheKB dir: `data/phekb-raw/statins-and-mace/`
- PheKB codes: {'ICD-9-CM': 3, 'CPT': 28}
- Module codes: SNOMED=['22298006', '50849002'], RxNorm=['83367'], LOINC=['10839-9']
- PheKB files to read: ['AMI_ALGORITHMS_20130926.docx']
- Algorithm summary: The phenotype identifies patients with Major Adverse Cardiac Events (MACE) while on statins, divided into two types: revascularization events and acute myocardial infarction (AMI). For AMI on statins, requires at least 2 ICD-9 codes (410.* or 411.*) within 5 days, confirmed lab values (Troponin-I ≥0...

### steroid-induced-avn

- PheKB dir: `data/phekb-raw/steroid-induced-osteonecrosis/`
- PheKB codes: {'ICD-9-CM': 49, 'CPT': 40}
- Module codes: SNOMED=['203483005'], RxNorm=['8640'], LOINC=[]
- PheKB files to read: ['Steroid20ON20phenotype20definition_Jan_10_2013.docx']
- Algorithm summary: This phenotype identifies steroid-induced osteonecrosis cases by requiring exposure to systemic corticosteroid medications (IV, IM, or PO routes only) while excluding patients with other known risk factors for osteonecrosis. The algorithm excludes patients with alcohol abuse, sickle cell disease, Ga...

### systemic-lupus-erythematosus

- PheKB dir: `data/phekb-raw/sle-systemic-lupus-erythematosus-using-slicc-systemic-lupus-internation-collaborating/`
- PheKB codes: {'ICD-9-CM': 10, 'ICD-10-CM': 14, 'LOINC': 11, 'RxNorm': 6, 'CPT': 1}
- Module codes: SNOMED=['239887007', '239890001', '295101000119105', '309762007', '55464009'], RxNorm=['1256', '265323', '5521', '6851', '8640'], LOINC=['5048-4']
- PheKB files to read: ['emerge_lupus_pseudocode_V4-64_2.docx', 'emerge_lupus_pseudocode_V5-4_with_NLP.docx', 'FINAL_SLE_SLICC_SQL_code_w_vocab_codes_inc_LOINC_eMERGE_3.docx', 'Supplemental20Data.LSM_.R1.20210330.docx']
- Algorithm summary: The SLE phenotype algorithm uses SLICC (Systemic Lupus International Collaborating Clinics) criteria to identify patients with Systemic Lupus Erythematosus. To have SLE according to SLICC, a patient must have: 1) at least four criteria, with at least one clinical criterion AND one immunologic criter...

### type-1-diabetes

- PheKB dir: `data/phekb-raw/type-1-and-type-2-diabetes-mellitus/`
- PheKB codes: {'ICD-9-CM': 1, 'ICD-10-CM': 2, 'LOINC': 7, 'RxNorm': 33}
- Module codes: SNOMED=['190368000', '199229001', '23045005', '31321000119102', '46635009'], RxNorm=['253182', '274783', '311036', '575068', '5856'], LOINC=['4548-4']
- PheKB files to read: ['diabetes_phenotype_RS.pdf']
- Algorithm summary: The algorithm identifies diabetes patients using ICD-9/ICD-10 diagnosis codes (250.x, E10.x, E11.x) combined with either abnormal lab values (random glucose >200 mg/dl, fasting glucose ≥125 mg/dl, HbA1c ≥6.5%) or diabetes-related medications. For T1DM vs T2DM classification, it uses a modified Klomp...

### type-2-diabetes

- PheKB dir: `data/phekb-raw/type-2-diabetes-t2d/`
- PheKB codes: {'ICD-9-CM': 8, 'ICD-10-CM': 7, 'SNOMED CT': 9, 'LOINC': 9}
- Module codes: SNOMED=['44054006', '73211009', '9414007'], RxNorm=['199246', '310490', '310537', '312440', '665033', '860975'], LOINC=['1558-6', '2339-0', '4548-4']
- PheKB files to read: ['Type20220Diabetes.pdf']
- Algorithm summary: Two T2D case algorithms are provided: preferred (t2d_dprism_ehr_plus_1) includes self-reported survey data, alternative (t2d_dprism_ehr_1) uses EHR only. Cases require: 1) Exclusion of T1D diagnoses, 2) T2D ICD codes with diabetes medications (insulin requires additional non-insulin medication or ≥2...

### urinary-incontinence

- PheKB dir: `data/phekb-raw/urinary-incontinence/`
- PheKB codes: {'ICD-9-CM': 1, 'ICD-10-CM': 1, 'CPT': 1}
- Module codes: SNOMED=['165232002'], RxNorm=['119565', '322167', '32675'], LOINC=[]
- PheKB files to read: ['PheKB_UI.docx']
- Algorithm summary: A weakly supervised machine learning approach that extracts urinary incontinence status from clinical narratives for prostate cancer patients. The algorithm uses weighted neural word embeddings with TF-idf scoring and domain-specific dictionaries combined with CLEVER terminology for weak supervision...

### venous-thromboembolism

- PheKB dir: `data/phekb-raw/venous-thromboembolism-vte/`
- PheKB codes: {'ICD-9-CM': 36}
- Module codes: SNOMED=['128053003', '234044007', '234049002', '281595001', '59282003'], RxNorm=['1037042', '1114195', '11289', '1364430', '67108'], LOINC=['48065-7']
- PheKB files to read: ['Mayo_VU_VTE_Algorithm_August242012.pdf']
- Algorithm summary: This is a two-step NLP-based phenotyping algorithm for Venous Thromboembolism (VTE). Step 1 uses natural language processing to identify positive VTE cases through either: (1) co-occurrence of disorder-related terms (clot, thrombosis, etc.) with anatomical site terms (vein, pulmonary, etc.) in the s...

### warfarin-dose-response

- PheKB dir: `data/phekb-raw/warfarin-doseresponse/`
- PheKB codes: {}
- Module codes: SNOMED=[], RxNorm=['11289'], LOINC=['6301-6']
- PheKB files to read: ['Warfarin20dose_response20phenotype20definition_current.docx']
- Algorithm summary: This algorithm identifies patients with stable INR values within the therapeutic range (2-3) maintained for at least three weeks, and correlates these stable INR values with their corresponding warfarin weekly dose. The purpose is to identify pharmacogenetic factors that influence warfarin stable do...

