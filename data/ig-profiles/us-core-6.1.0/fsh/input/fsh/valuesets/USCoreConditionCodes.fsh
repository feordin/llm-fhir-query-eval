ValueSet: USCoreConditionCodes
Id: us-core-condition-code
Title: "US Core Condition Codes"
Description: "This describes the problem. Diagnosis/Problem List is broadly defined as a series of brief statements that catalog a patient's medical, nursing, dental, social, preventative and psychiatric events and issues that are relevant to that patient's healthcare (e.g., signs, symptoms, and defined conditions). ICD-10 is appropriate for Diagnosis information, and ICD-9 for historical information."
* ^meta.versionId = "1"
* ^meta.lastUpdated = "2022-04-28T00:15:18.578000+00:00"
* ^status = #active
* ^experimental = false
* ^date = "2022-09-29"
* ^copyright = "1. This value set includes content from SNOMED CT, which is copyright © 2002+ International Health Terminology Standards Development Organisation (IHTSDO), and distributed by agreement between IHTSDO and HL7. Implementer use of SNOMED CT is not covered by this agreement.\n2. ICD-9 and ICD-10 are copyrighted by the World Health Organization (WHO) which owns and publishes the classification. See https://www.who.int/classifications/icd/en. WHO has authorized the development of an adaptation of ICD-9 and ICD-10 to ICD-9-CM to ICD-10-CM for use in the United States for U.S. government purposes."
* SNOMED_CT#160245001
* include codes from system SNOMED_CT where concept is-a #404684003
* include codes from system SNOMED_CT where concept is-a #243796009
* include codes from system SNOMED_CT where concept is-a #272379006
* include codes from system http://hl7.org/fhir/sid/icd-10-cm
* include codes from system http://hl7.org/fhir/sid/icd-9-cm