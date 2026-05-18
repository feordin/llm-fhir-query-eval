# Test-data rigor audit -- 2026-05-17

Surfaced while investigating asthma-comprehensive == asthma-meds == 76.

## Q1 -- Path B (dx-only) coverage across phenotype modules

The 3-path Synthea template (A: dx+meds, B: dx-only, C: meds-only, D: labs-only)
is the mechanism for generating realistic messy records. Where Path B is absent,
every diagnosed patient is also on meds, so dx is a subset of meds and
`comprehensive == meds` for those phenotypes.

| Phenotype | A | B | C | D | Notes |
|---|:-:|:-:|:-:|:-:|---|
| `abdominal_aortic_aneurysm` | - | - | - | - | missing path(s): ABC |
| `ace_inhibitor_cough` | - | - | - | - | missing path(s): ABC |
| `acute_kidney_injury` | - | - | y | - | missing path(s): AB |
| `adhd` | - | - | y | - | missing path(s): AB |
| `alcohol_use_disorder` | y | y | y | - |  |
| `anxiety` | - | - | y | - | missing path(s): AB |
| `appendicitis` | - | - | - | - | missing path(s): ABC |
| `asthma` | - | - | y | - | missing path(s): AB |
| `asthma_response_inhaled_steroids` | y | y | y | - |  |
| `atopic_dermatitis` | - | - | - | - | missing path(s): ABC |
| `atrial_fibrillation` | - | - | y | - | missing path(s): AB |
| `autism` | - | - | y | - | missing path(s): AB |
| `autoimmune_disease` | - | - | - | - | missing path(s): ABC |
| `bipolar_disorder` | y | y | y | - |  |
| `bladder_cancer` | - | - | - | - | missing path(s): ABC |
| `bone_scan_utilization` | - | - | - | - | missing path(s): ABC |
| `bph` | y | y | y | - |  |
| `breast_cancer` | y | y | y | - |  |
| `ca_mrsa` | y | y | y | - |  |
| `cardiac_conduction_qrs` | - | - | - | - | missing path(s): ABC |
| `cardiorespiratory_fitness` | - | - | - | - | missing path(s): ABC |
| `carotid_atherosclerosis` | y | y | y | - |  |
| `cataracts` | y | y | y | y |  |
| `cervical_cancer` | y | y | y | - |  |
| `chronic_rhinosinusitis` | y | y | y | - |  |
| `ckd` | y | y | y | y |  |
| `clopidogrel_poor_metabolizers` | y | y | y | - |  |
| `clostridium_difficile` | y | y | y | - |  |
| `colorectal_cancer` | y | y | y | y |  |
| `copd` | y | y | y | - |  |
| `coronary_heart_disease` | y | y | y | y |  |
| `crohns_disease` | y | y | y | y |  |
| `cystic_fibrosis` | - | - | - | - | missing path(s): ABC |
| `dementia` | y | y | y | - |  |
| `depression` | y | y | y | - |  |
| `developmental_language_disorder` | - | - | - | - | missing path(s): ABC |
| `diabetic_retinopathy` | y | y | y | - |  |
| `digital_rectal_exam` | - | - | - | - | missing path(s): ABC |
| `diverticulitis` | y | y | y | - |  |
| `down_syndrome` | - | - | - | - | missing path(s): ABC |
| `drug_induced_liver_injury` | y | y | y | y |  |
| `endometriosis` | y | y | y | - |  |
| `epilepsy` | y | y | y | y |  |
| `esophageal_cancer` | - | - | - | - | missing path(s): ABC |
| `familial_hypercholesterolemia` | y | y | y | y |  |
| `febrile_neutropenia_pediatric` | y | y | y | - |  |
| `fibromyalgia` | y | y | y | - |  |
| `functional_seizures` | - | - | - | - | missing path(s): ABC |
| `gerd` | y | y | y | - |  |
| `glaucoma` | y | y | y | - |  |
| `glioblastoma` | - | - | - | - | missing path(s): ABC |
| `gout` | y | y | y | y |  |
| `hearing_loss` | - | - | - | - | missing path(s): ABC |
| `heart_failure` | y | y | y | y |  |
| `hepatitis_c` | y | y | y | y |  |
| `herpes_zoster` | y | y | y | - |  |
| `hiv` | y | y | y | y |  |
| `hypertension` | y | y | y | y |  |
| `hyperthyroidism` | y | y | y | y |  |
| `hypothyroidism` | y | y | y | y |  |
| `influenza` | y | y | y | - |  |
| `intellectual_disability` | - | - | - | - | missing path(s): ABC |
| `iron_deficiency_anemia` | y | y | y | y |  |
| `leukemia` | - | - | - | - | missing path(s): ABC |
| `liver_cancer` | y | y | y | y |  |
| `liver_cancer_staging` | - | - | - | - | missing path(s): ABC |
| `lung_cancer` | - | - | - | - | missing path(s): ABC |
| `lyme_disease` | y | y | y | - |  |
| `lymphoma` | - | - | - | - | missing path(s): ABC |
| `melanoma` | - | - | - | - | missing path(s): ABC |
| `migraine` | y | y | y | - |  |
| `multimodal_analgesia` | y | y | y | - |  |
| `multiple_myeloma` | - | - | - | - | missing path(s): ABC |
| `multiple_sclerosis` | y | y | y | - |  |
| `nafld` | y | y | y | y |  |
| `neonatal_abstinence_syndrome` | y | y | y | - |  |
| `osteoporosis` | y | y | y | y |  |
| `ovarian_cancer` | y | y | y | y |  |
| `pancreatic_cancer` | y | y | y | y |  |
| `parkinsons_disease` | y | y | y | - |  |
| `peanut_allergy` | y | y | y | - |  |
| `peripheral_arterial_disease` | y | y | y | - |  |
| `pneumonia` | y | y | y | - |  |
| `polycystic_kidney_disease` | - | - | - | - | missing path(s): ABC |
| `post_event_pain` | - | - | - | - | missing path(s): ABC |
| `prostate_cancer` | y | y | y | y |  |
| `psoriasis` | y | y | y | - |  |
| `renal_cancer` | - | - | - | - | missing path(s): ABC |
| `resistant_hypertension` | y | y | y | - |  |
| `rheumatoid_arthritis` | y | y | y | y |  |
| `schizophrenia` | y | y | y | - |  |
| `sepsis` | y | y | y | y |  |
| `severe_childhood_obesity` | y | y | y | y |  |
| `sickle_cell_disease` | y | y | y | - |  |
| `sleep_apnea` | y | y | y | y |  |
| `statins_and_mace` | y | y | y | - |  |
| `steroid_induced_avn` | y | y | y | - |  |
| `stomach_cancer` | - | - | - | - | missing path(s): ABC |
| `stroke` | y | y | y | - |  |
| `systemic_lupus_erythematosus` | y | y | y | y |  |
| `thyroid_cancer` | - | - | - | - | missing path(s): ABC |
| `tuberculosis` | y | y | y | - |  |
| `type_1_diabetes` | y | y | y | - |  |
| `type_2_diabetes` | - | - | - | - | missing path(s): ABC |
| `ulcerative_colitis` | y | y | y | - |  |
| `urinary_incontinence` | y | y | y | - |  |
| `venous_thromboembolism` | y | y | y | y |  |
| `warfarin_dose_response` | y | y | y | - |  |

## Q4 -- Control rigor: existing comorbidities + proposed mimicker upgrades

Of 108 control modules, 94 have NO conditions modeled (pure-healthy).
F1 scores against pure-healthy controls overstate true model skill: broad
queries cannot be falsely matched if controls have nothing to match.

Proposed mimickers are clinically recognized differential diagnoses;
SNOMED codes still need UMLS/VSAC lookup before module edits.

| Phenotype | Current control conditions | Proposed mimickers to add |
|---|---|---|
| `abdominal_aortic_aneurysm` | Hypertensive disorder, Peripheral arterial occlusive disease, Hyperlipidemia | *(needs research)* |
| `ace_inhibitor_cough` | Hypertensive disorder, Hypertensive disorder, Hyperlipidemia | *(needs research)* |
| `acute_kidney_injury` | Hypertensive disorder, Urinary tract infectious disease | CKD, Dehydration, Urinary obstruction |
| `adhd` | Common cold, Otitis media, Allergic rhinitis | *(needs research)* |
| `alcohol_use_disorder` | *(pure-healthy)* | *(needs research)* |
| `anxiety` | Hypertensive disorder, Allergic rhinitis | Hyperthyroidism, Pheochromocytoma, Cardiac arrhythmia |
| `appendicitis` | Gastroenteritis, Abdominal pain, Gastroesophageal reflux disease | *(needs research)* |
| `asthma` | Hypertensive disorder, Allergic rhinitis, Gastroesophageal reflux disease | COPD, Chronic bronchitis, Eosinophilic bronchitis, Vocal cord dysfunction |
| `asthma_response_inhaled_steroids` | *(pure-healthy)* | *(needs research)* |
| `atopic_dermatitis` | Hypertensive disorder, Hyperlipidemia | Contact dermatitis, Psoriasis, Seborrheic dermatitis |
| `atrial_fibrillation` | Hypertensive disorder, Hyperlipidemia, Heart failure | Atrial flutter, MAT, SVT, Sinus tachycardia |
| `autism` | Otitis media, Upper respiratory infection | *(needs research)* |
| `autoimmune_disease` | *(pure-healthy)* | *(needs research)* |
| `bipolar_disorder` | *(pure-healthy)* | Major depression (unipolar), Cyclothymia, Borderline PD, Substance-induced mood |
| `bladder_cancer` | *(pure-healthy)* | *(needs research)* |
| `bone_scan_utilization` | *(pure-healthy)* | *(needs research)* |
| `bph` | *(pure-healthy)* | *(needs research)* |
| `breast_cancer` | *(pure-healthy)* | *(needs research)* |
| `ca_mrsa` | *(pure-healthy)* | *(needs research)* |
| `cardiac_conduction_qrs` | *(pure-healthy)* | *(needs research)* |
| `cardiorespiratory_fitness` | *(pure-healthy)* | *(needs research)* |
| `carotid_atherosclerosis` | *(pure-healthy)* | *(needs research)* |
| `cataracts` | *(pure-healthy)* | *(needs research)* |
| `cervical_cancer` | *(pure-healthy)* | *(needs research)* |
| `chronic_rhinosinusitis` | *(pure-healthy)* | *(needs research)* |
| `ckd` | *(pure-healthy)* | AKI, Polycystic kidney disease, Glomerulonephritis |
| `clopidogrel_poor_metabolizers` | *(pure-healthy)* | *(needs research)* |
| `clostridium_difficile` | *(pure-healthy)* | *(needs research)* |
| `colorectal_cancer` | *(pure-healthy)* | *(needs research)* |
| `copd` | *(pure-healthy)* | Asthma, Bronchiectasis, Heart failure, Pulmonary fibrosis |
| `coronary_heart_disease` | *(pure-healthy)* | GERD, Costochondritis, Pericarditis, Aortic dissection |
| `crohns_disease` | *(pure-healthy)* | UC, IBS, Celiac disease, Microscopic colitis |
| `cystic_fibrosis` | *(pure-healthy)* | *(needs research)* |
| `dementia` | Osteoarthritis (disorder), Hyperlipidemia (disorder) | Mild cognitive impairment, Depression (pseudodementia), Delirium, Normal aging |
| `depression` | Essential hypertension (disorder), Hyperlipidemia (disorder) | Bipolar disorder, Adjustment disorder, Hypothyroidism, Anemia |
| `developmental_language_disorder` | *(pure-healthy)* | *(needs research)* |
| `diabetic_retinopathy` | *(pure-healthy)* | *(needs research)* |
| `digital_rectal_exam` | *(pure-healthy)* | *(needs research)* |
| `diverticulitis` | *(pure-healthy)* | *(needs research)* |
| `down_syndrome` | *(pure-healthy)* | *(needs research)* |
| `drug_induced_liver_injury` | *(pure-healthy)* | *(needs research)* |
| `endometriosis` | *(pure-healthy)* | *(needs research)* |
| `epilepsy` | *(pure-healthy)* | Syncope, PNES, TIA, Migraine |
| `esophageal_cancer` | *(pure-healthy)* | *(needs research)* |
| `familial_hypercholesterolemia` | *(pure-healthy)* | *(needs research)* |
| `febrile_neutropenia_pediatric` | *(pure-healthy)* | *(needs research)* |
| `fibromyalgia` | *(pure-healthy)* | CFS, Polymyalgia rheumatica, Hypothyroidism |
| `functional_seizures` | *(pure-healthy)* | *(needs research)* |
| `gerd` | *(pure-healthy)* | Peptic ulcer, Eosinophilic esophagitis, Functional dyspepsia, Cardiac chest pain |
| `glaucoma` | *(pure-healthy)* | *(needs research)* |
| `glioblastoma` | *(pure-healthy)* | *(needs research)* |
| `gout` | *(pure-healthy)* | Pseudogout (CPPD), Septic arthritis, RA |
| `hearing_loss` | *(pure-healthy)* | *(needs research)* |
| `heart_failure` | *(pure-healthy)* | COPD, Pulmonary embolism, Liver cirrhosis, CKD |
| `hepatitis_c` | *(pure-healthy)* | *(needs research)* |
| `herpes_zoster` | *(pure-healthy)* | *(needs research)* |
| `hiv` | *(pure-healthy)* | *(needs research)* |
| `hypertension` | *(pure-healthy)* | White coat hypertension, Secondary HTN (renal), Preeclampsia |
| `hyperthyroidism` | *(pure-healthy)* | Anxiety disorder, Pheochromocytoma, Substance use |
| `hypothyroidism` | *(pure-healthy)* | Depression, Anemia, CFS, Sick euthyroid |
| `influenza` | *(pure-healthy)* | *(needs research)* |
| `intellectual_disability` | *(pure-healthy)* | *(needs research)* |
| `iron_deficiency_anemia` | *(pure-healthy)* | Anemia of chronic disease, Thalassemia trait, B12 deficiency |
| `leukemia` | *(pure-healthy)* | *(needs research)* |
| `liver_cancer` | *(pure-healthy)* | *(needs research)* |
| `liver_cancer_staging` | *(pure-healthy)* | *(needs research)* |
| `lung_cancer` | *(pure-healthy)* | *(needs research)* |
| `lyme_disease` | *(pure-healthy)* | *(needs research)* |
| `lymphoma` | *(pure-healthy)* | *(needs research)* |
| `melanoma` | *(pure-healthy)* | *(needs research)* |
| `migraine` | *(pure-healthy)* | Tension headache, Cluster headache, MOH, Sinusitis |
| `multimodal_analgesia` | *(pure-healthy)* | *(needs research)* |
| `multiple_myeloma` | *(pure-healthy)* | *(needs research)* |
| `multiple_sclerosis` | *(pure-healthy)* | Neuromyelitis optica, ADEM, Migraine, B12 deficiency |
| `nafld` | *(pure-healthy)* | *(needs research)* |
| `neonatal_abstinence_syndrome` | *(pure-healthy)* | *(needs research)* |
| `osteoporosis` | *(pure-healthy)* | Osteopenia, Osteomalacia, Multiple myeloma |
| `ovarian_cancer` | *(pure-healthy)* | *(needs research)* |
| `pancreatic_cancer` | *(pure-healthy)* | *(needs research)* |
| `parkinsons_disease` | *(pure-healthy)* | Essential tremor, Drug-induced parkinsonism, Lewy body dementia |
| `peanut_allergy` | *(pure-healthy)* | *(needs research)* |
| `peripheral_arterial_disease` | *(pure-healthy)* | *(needs research)* |
| `pneumonia` | *(pure-healthy)* | Bronchitis, COPD exacerbation, Asthma exacerbation, Heart failure |
| `polycystic_kidney_disease` | *(pure-healthy)* | *(needs research)* |
| `post_event_pain` | *(pure-healthy)* | *(needs research)* |
| `prostate_cancer` | *(pure-healthy)* | *(needs research)* |
| `psoriasis` | *(pure-healthy)* | Atopic dermatitis, Seborrheic dermatitis, Tinea corporis |
| `renal_cancer` | *(pure-healthy)* | *(needs research)* |
| `resistant_hypertension` | *(pure-healthy)* | *(needs research)* |
| `rheumatoid_arthritis` | *(pure-healthy)* | Osteoarthritis, Psoriatic arthritis, Lupus, Fibromyalgia |
| `schizophrenia` | *(pure-healthy)* | Schizoaffective disorder, Bipolar with psychosis, Substance-induced psychosis |
| `sepsis` | *(pure-healthy)* | *(needs research)* |
| `severe_childhood_obesity` | *(pure-healthy)* | *(needs research)* |
| `sickle_cell_disease` | Sickle cell trait | *(needs research)* |
| `sleep_apnea` | *(pure-healthy)* | *(needs research)* |
| `statins_and_mace` | *(pure-healthy)* | *(needs research)* |
| `steroid_induced_avn` | *(pure-healthy)* | *(needs research)* |
| `stomach_cancer` | *(pure-healthy)* | *(needs research)* |
| `stroke` | *(pure-healthy)* | TIA, Migraine with aura, Bell palsy, Hypoglycemia, Seizure |
| `systemic_lupus_erythematosus` | *(pure-healthy)* | RA, Sjogren syndrome, MCTD |
| `thyroid_cancer` | *(pure-healthy)* | *(needs research)* |
| `tuberculosis` | *(pure-healthy)* | *(needs research)* |
| `type_1_diabetes` | *(pure-healthy)* | Type 2 diabetes, MODY, LADA |
| `type_2_diabetes` | Hypertensive disorder, Hyperlipidemia | Type 1 diabetes, Gestational diabetes, Prediabetes |
| `ulcerative_colitis` | *(pure-healthy)* | Crohn disease, Infectious colitis, Ischemic colitis, IBS |
| `urinary_incontinence` | *(pure-healthy)* | *(needs research)* |
| `venous_thromboembolism` | *(pure-healthy)* | Cellulitis, Baker cyst, Muscle strain |
| `warfarin_dose_response` | *(pure-healthy)* | *(needs research)* |

## Summary stats

- Phenotypes missing Path B: 36
- Phenotypes missing Path C: 30
- Phenotypes with pure-healthy controls: 94
- Phenotypes with proposed mimicker pack: 35
- Phenotypes still needing mimicker research: 73
