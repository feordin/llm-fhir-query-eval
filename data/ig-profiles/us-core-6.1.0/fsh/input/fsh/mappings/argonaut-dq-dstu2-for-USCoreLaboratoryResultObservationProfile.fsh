// WARNING: The following Mapping may be incomplete since the original USCoreLaboratoryResultObservationProfile
// StructureDefinition was missing the mapping entry for argonaut-dq-dstu2.
// Please review this and add the following properties as necessary: Target, Title, Description
Mapping: argonaut-dq-dstu2-for-USCoreLaboratoryResultObservationProfile
Id: argonaut-dq-dstu2
Source: USCoreLaboratoryResultObservationProfile
* category[us-core] -> "Observation.category"
* code -> "Observation.code"
* value[x] -> "Observation.value[x]"