// WARNING: The following Mapping may be incomplete since the original USCoreMedicationRequestProfile
// StructureDefinition was missing the mapping entry for argonaut-dq-dstu2.
// Please review this and add the following properties as necessary: Target, Title, Description
Mapping: argonaut-dq-dstu2-for-USCoreMedicationRequestProfile
Id: argonaut-dq-dstu2
Source: USCoreMedicationRequestProfile
* -> "MedicationOrder"
* status -> "MedicationOrder.status"
* intent -> "MedicationOrder.status"
* reported[x] -> "MedicationOrder.status"
* medication[x] -> "MedicationOrder.medication[x]"
* subject -> "MedicationOrder.patient"
* encounter -> "NA"
* authoredOn -> "MedicationOrder.dateWritten"
* requester -> "MedicationOrder.prescriber"