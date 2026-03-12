// WARNING: The following Mapping may be incomplete since the original USCorePatientProfile
// StructureDefinition was missing the mapping entry for argonaut-dq-dstu2.
// Please review this and add the following properties as necessary: Target, Title, Description
Mapping: argonaut-dq-dstu2-for-USCorePatientProfile
Id: argonaut-dq-dstu2
Source: USCorePatientProfile
* -> "Patient"
* extension[race] -> "Patient.extension"
* extension[ethnicity] -> "Patient.extension"
* extension[birthsex] -> "Patient.extension"
* identifier -> "Patient.identifier"
* identifier.system -> "Patient.identifier.system"
* identifier.value -> "Patient.identifier.value"
* name -> "Patient.name"
* name.family -> "Patient.name.family"
* name.given -> "Patient.name.given"
* name.suffix -> "NA"
* name.period -> "NA"
* telecom -> "NA"
* telecom.system -> "NA"
* telecom.value -> "NA"
* telecom.use -> "NA"
* gender -> "Patient.gender"
* birthDate -> "Patient.birthDate"
* address -> "Patient.birthDate"
* address.line -> "NA"
* address.city -> "NA"
* address.state -> "NA"
* address.postalCode -> "NA"
* address.period -> "NA"
* communication -> "Patient.communication"
* communication.language -> "Patient.communication.language"