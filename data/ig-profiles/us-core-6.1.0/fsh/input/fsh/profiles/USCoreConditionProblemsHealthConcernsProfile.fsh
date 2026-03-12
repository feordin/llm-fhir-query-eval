Profile: USCoreConditionProblemsHealthConcernsProfile
Parent: Condition
Id: us-core-condition-problems-health-concerns
Title: "US Core Condition Problems and Health Concerns Profile"
Description: "The US Core Condition Problems and Health Concerns Profile is based upon the core FHIR Condition Resource and meets the  U.S. Core Data for Interoperability (USCDI) v2 'Problems' and 'Health Concerns' requirements and SDOH 'Problems/Health Concerns' requirements.  In version 5.0.0, The US Core Condition Profile has been split into the US Core Condition Encounter Diagnosis Profile and US Core Condition Problems and Health Concerns Profile.  To promote interoperability and adoption through common implementation, this profile defines constraints and extensions on the Condition resource for the minimal set of data to record, search, and fetch information about a condition, diagnosis, or other event, situation, issue, or clinical concept that is documented and categorized as a problem or health concern including information about a Social Determinants of Health-related condition. It identifies which core elements, extensions, vocabularies, and value sets **SHALL** be present in the resource when and constrains the way the elements are used using this profile. It provides the floor for standards development for specific use cases."
* ^status = #active
* ^experimental = false
* ^date = "2022-04-20"
* . ^definition = "\\-"
* . ^comment = "\\-"
* . ^mustSupport = false
* extension contains ConditionAssertedDate named assertedDate 0..1 MS
* extension[assertedDate] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* extension[assertedDate] ^extension.valueBoolean = true
* extension[assertedDate] ^short = "(USCDI) Date the condition was first asserted"
* clinicalStatus MS
* clinicalStatus from ConditionClinicalStatusCodes (required)
* clinicalStatus ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* clinicalStatus ^extension.valueBoolean = true
* clinicalStatus ^short = "(USCDI) active | recurrence | relapse | inactive | remission | resolved"
* verificationStatus MS
* verificationStatus from ConditionVerificationStatus (required)
* verificationStatus ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* verificationStatus ^extension.valueBoolean = true
* verificationStatus ^short = "(USCDI) unconfirmed | provisional | differential | confirmed | refuted | entered-in-error"
* category MS
* category ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* category ^extension.valueBoolean = true
* category ^slicing.discriminator.type = #pattern
* category ^slicing.discriminator.path = "$this"
* category ^slicing.rules = #open
* category ^short = "(USCDI) category codes"
* category contains
    us-core 1..* MS and
    screening-assessment 0..* MS
* category[us-core] from http://hl7.org/fhir/us/core/ValueSet/us-core-problem-or-health-concern (required)
* category[us-core] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* category[us-core] ^extension.valueBoolean = true
* category[us-core] ^short = "(USCDI) problem-list-item | health-concern"
* category[us-core] ^binding.description = "Note that other codes are permitted, see [Required Bindings When Slicing by Value Sets](http://hl7.org/fhir/us/core/general-requirements.html#required-bindings-when-slicing-by-valuesets)"
* category[screening-assessment] from http://hl7.org/fhir/us/core/ValueSet/us-core-screening-assessment-condition-category (required)
* category[screening-assessment] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* category[screening-assessment] ^extension.valueBoolean = true
* category[screening-assessment] ^short = "(USCDI) USCDI Health Status/Assessments Data Class"
* category[screening-assessment] ^definition = "Categories that a provider may use in their workflow to classify that this Condition is related to a USCDI Health Status/Assessments Data Class."
* category[screening-assessment] ^requirements = "Used for filtering condition"
* category[screening-assessment] ^binding.description = "Note that other codes are permitted, see [Required Bindings When Slicing by Value Sets](http://hl7.org/fhir/us/core/general-requirements.html#required-bindings-when-slicing-by-valuesets)"
* code 1.. MS
* code from USCoreConditionCodes (extensible)
* code ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* code ^extension.valueBoolean = true
* code ^short = "(USCDI) Identification of the condition, problem or diagnosis"
* code ^binding.description = "Valueset to describe the actual problem experienced by the patient"
* subject only Reference(USCorePatientProfile)
* subject MS
* subject ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* subject ^extension.valueBoolean = true
* subject ^short = "(USCDI) Who has the condition?"
* onset[x] only dateTime or Age or Period or Range or string
* onset[x] MS
* onset[x] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* onset[x] ^extension.valueBoolean = true
* onset[x] ^short = "(USCDI) Estimated or actual date,  date-time, or age"
* onset[x] ^type.extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* onset[x] ^type.extension.valueBoolean = true
* abatement[x] only dateTime or Age or Period or Range or string
* abatement[x] MS
* abatement[x] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* abatement[x] ^extension.valueBoolean = true
* abatement[x] ^short = "(USCDI) When in resolution/remission"
* abatement[x] ^type.extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* abatement[x] ^type.extension.valueBoolean = true
* recordedDate MS
* recordedDate ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* recordedDate ^extension.valueBoolean = true
* recordedDate ^short = "(USCDI) Date record was first recorded"