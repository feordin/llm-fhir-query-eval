Profile: USCoreMedicationRequestProfile
Parent: MedicationRequest
Id: us-core-medicationrequest
Title: "US Core MedicationRequest Profile"
Description: "The US Core Medication Request Profile is based upon the core FHIR MedicationRequest Resource and meets the U.S. Core Data for Interoperability (USCDI) v2 *Medications* requirements. The MedicationRequest resource can be used to record a patient's medication prescription or order.  This profile sets minimum expectations for the MedicationRequest resource to record, search, and fetch a patient's medication to promote interoperability and adoption through common implementation.  It identifies which core elements, extensions, vocabularies, and value sets **SHALL** be present in the resource and constrains the way the elements are used when using this profile.  It provides the floor for standards development for specific use cases."
* ^version = "3.1.1"
* ^status = #active
* ^experimental = false
* ^date = "2020-06-26"
* ^publisher = "HL7 US Realm Steering Committee"
* ^contact.telecom.system = #url
* ^contact.telecom.value = "http://www.healthit.gov"
* ^jurisdiction = urn:iso:std:iso:3166#US "United States of America"
* obeys us-core-21
* . ^definition = "\\-"
* . ^comment = "\\-"
* . ^mustSupport = false
* status MS
* status from http://hl7.org/fhir/ValueSet/medicationrequest-status (required)
* status ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* status ^extension.valueBoolean = true
* status ^short = "(USCDI) active | on-hold | cancelled | completed | entered-in-error | stopped | draft | unknown"
* status ^binding.description = "A code specifying the state of the prescribing event. Describes the lifecycle of the prescription."
* intent MS
* intent from http://hl7.org/fhir/ValueSet/medicationrequest-intent (required)
* intent ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* intent ^extension.valueBoolean = true
* intent ^short = "(USCDI) proposal | plan | order | original-order | reflex-order | filler-order | instance-order | option"
* intent ^condition = "us-core-21"
* intent ^binding.description = "The kind of medication order."
* category MS
* category ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* category ^extension.valueBoolean = true
* category ^slicing.discriminator.type = #pattern
* category ^slicing.discriminator.path = "$this"
* category ^slicing.rules = #open
* category ^short = "(USCDI) Type of medication usage"
* category contains us-core 0..* MS
* category[us-core] from http://hl7.org/fhir/ValueSet/medicationrequest-category (required)
* category[us-core] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* category[us-core] ^extension.valueBoolean = true
* category[us-core] ^short = "(USCDI) Type of medication usage"
* category[us-core] ^binding.description = "The type of medication order. Note that other codes are permitted, see [Required Bindings When Slicing by Value Sets](http://hl7.org/fhir/us/core/general-requirements.html#required-bindings-when-slicing-by-valuesets)"
* reported[x] only boolean or Reference(http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitioner or http://hl7.org/fhir/us/core/StructureDefinition/us-core-organization or USCorePatientProfile or http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitionerrole or http://hl7.org/fhir/us/core/StructureDefinition/us-core-relatedperson)
* reported[x] MS
* reported[x] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* reported[x] ^extension.valueBoolean = true
* reported[x] ^short = "(USCDI) Reported rather than primary record"
* reported[x] ^type[0].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].extension.valueBoolean = true
* reported[x] ^type[+].targetProfile[0].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].targetProfile[=].extension.valueBoolean = true
* reported[x] ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].targetProfile[=].extension.valueBoolean = false
* reported[x] ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].targetProfile[=].extension.valueBoolean = false
* reported[x] ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].targetProfile[=].extension.valueBoolean = false
* reported[x] ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].targetProfile[=].extension.valueBoolean = false
* reported[x] ^type[=].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* reported[x] ^type[=].extension.valueBoolean = true
* medication[x] only CodeableConcept or Reference(http://hl7.org/fhir/us/core/StructureDefinition/us-core-medication)
* medication[x] MS
* medication[x] from http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113762.1.4.1010.4 (extensible)
* medication[x] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* medication[x] ^extension.valueBoolean = true
* medication[x] ^short = "(USCDI) Medication to be taken"
* subject only Reference(USCorePatientProfile)
* subject MS
* subject ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* subject ^extension.valueBoolean = true
* subject ^short = "(USCDI) Who or group medication request is for"
* encounter only Reference(http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter)
* encounter MS
* encounter ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* encounter ^extension.valueBoolean = true
* encounter ^short = "(USCDI) Encounter created as part of encounter/admission/stay"
* authoredOn MS
* authoredOn ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* authoredOn ^extension.valueBoolean = true
* authoredOn ^short = "(USCDI) When request was initially authored"
* requester only Reference(http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitioner or USCorePatientProfile or http://hl7.org/fhir/us/core/StructureDefinition/us-core-organization or http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitionerrole or http://hl7.org/fhir/us/core/StructureDefinition/us-core-relatedperson or Device)
* requester MS
* requester ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* requester ^extension.valueBoolean = true
* requester ^short = "(USCDI) Who/What requested the Request"
* requester ^type[0].targetProfile[0].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* requester ^type[=].targetProfile[=].extension.valueBoolean = true
* requester ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* requester ^type[=].targetProfile[=].extension.valueBoolean = false
* requester ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* requester ^type[=].targetProfile[=].extension.valueBoolean = false
* requester ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* requester ^type[=].targetProfile[=].extension.valueBoolean = false
* requester ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* requester ^type[=].targetProfile[=].extension.valueBoolean = false
* requester ^type[=].targetProfile[+].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* requester ^type[=].targetProfile[=].extension.valueBoolean = false
* requester ^condition = "us-core-21"
* reasonCode from USCoreConditionCodes (extensible)
* reasonCode ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* reasonCode ^extension.valueBoolean = true
* reasonCode ^short = "(USCDI) Reason or indication for ordering or not ordering the medication"
* reasonReference ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* reasonReference ^extension.valueBoolean = true
* reasonReference ^short = "(USCDI) US Core Condition or Observation that supports the prescription"
* dosageInstruction MS
* dosageInstruction ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dosageInstruction ^extension.valueBoolean = true
* dosageInstruction ^short = "(USCDI) How the medication should be taken"
* dosageInstruction.text MS
* dosageInstruction.text ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dosageInstruction.text ^extension.valueBoolean = true
* dosageInstruction.text ^short = "(USCDI) Free text dosage instructions e.g. SIG"
* dosageInstruction.timing MS
* dosageInstruction.timing ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dosageInstruction.timing ^extension.valueBoolean = true
* dosageInstruction.timing ^short = "(USCDI) When medication should be administered"
* dosageInstruction.doseAndRate MS
* dosageInstruction.doseAndRate ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dosageInstruction.doseAndRate ^extension.valueBoolean = true
* dosageInstruction.doseAndRate ^short = "(USCDI) Amount of medication administered"
* dosageInstruction.doseAndRate.dose[x] only Quantity or Range
* dosageInstruction.doseAndRate.dose[x] MS
* dosageInstruction.doseAndRate.dose[x] from http://hl7.org/fhir/ValueSet/ucum-common (preferred)
* dosageInstruction.doseAndRate.dose[x] ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dosageInstruction.doseAndRate.dose[x] ^extension.valueBoolean = true
* dosageInstruction.doseAndRate.dose[x] ^short = "(USCDI) Amount of medication per dose"
* dosageInstruction.doseAndRate.dose[x] ^type[0].extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-type-must-support"
* dosageInstruction.doseAndRate.dose[x] ^type[=].extension.valueBoolean = true
* dosageInstruction.doseAndRate.dose[x] ^binding.extension.url = "http://hl7.org/fhir/StructureDefinition/elementdefinition-maxValueSet"
* dosageInstruction.doseAndRate.dose[x] ^binding.extension.valueCanonical = "http://hl7.org/fhir/ValueSet/ucum-units"
* dispenseRequest MS
* dispenseRequest ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dispenseRequest ^extension.valueBoolean = true
* dispenseRequest ^short = "(USCDI) Medication supply authorization"
* dispenseRequest.numberOfRepeatsAllowed MS
* dispenseRequest.numberOfRepeatsAllowed ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dispenseRequest.numberOfRepeatsAllowed ^extension.valueBoolean = true
* dispenseRequest.numberOfRepeatsAllowed ^short = "(USCDI) Number of refills authorized"
* dispenseRequest.quantity MS
* dispenseRequest.quantity ^extension.url = "http://hl7.org/fhir/us/core/StructureDefinition/uscdi-requirement"
* dispenseRequest.quantity ^extension.valueBoolean = true
* dispenseRequest.quantity ^short = "(USCDI) Amount of medication to supply per dispense"