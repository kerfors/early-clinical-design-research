# Where this is heading

Master-protocol templates organise the documents: a master and its appendices, as in the EU-PEARL templates
([side by side](https://kerfors.github.io/early-clinical-design-research/templates/eupearl/)). What trials actually
share and change is design content: eligibility criteria, arms and doses, endpoints and instruments, schedule cells,
allocation rules. USDM v4.0 cannot hold that content once and reuse it: an inherited endpoint can only be copied
(BP05), and a new Core version means copying unchanged appendix content into a new study version (BP13)
([breakpoints](https://kerfors.github.io/early-clinical-design-research/usdm/)). And the documents give at most a
one-line rationale per change, never the alternatives considered
([Q10](https://kerfors.github.io/early-clinical-design-research/questions/Q10/)).

## First step: design content as Linked Data

The idea is design content as components, each with its own identifier, wherever it occurs. The relations are then
statements between identifiers: between layers (inherits, delegates, overridable default, restates, extends,
overrides), to the version of the layer a component depends on, and to decisions as objects of their own: who
decides, at which layer, bound to what, with which alternatives and arguments. Together these statements form a
graph. Published as Linked Data, with identifiers that resolve as in [m11-rdf](https://w3id.org/m11-rdf/), the graph
can be read and queried across trials and programmes.

The future this points to:

1. **Design in the model.** A trial is composed from reusable components with one identity across trials.
2. **Decisions captured where they are made**, with their arguments: the part no public document holds.
3. **Layers as relations, not chapters.** An unanswered delegation is a validation error, not a later finding.
4. **Documents as views.** The Core, DSA and ISA documents and an ICH M11 rendering are generated from the model.
   USDM and M11 become outputs, not mapping targets.
5. **Evolution is native.** An amendment changes a component or a decision, and every user of it is listed, to
   rebind or to stay.

Near term, USDM v4 stays the document carrier, with the design modules beside it for what it cannot carry
([USDM v4 and master protocols](https://kerfors.github.io/early-clinical-design-research/usdm/)); documents
generated from the model are the direction.

## Next step: the ontologies behind the content

Components in a graph are only a first part. Behind the content are classes and relations: an objective, the
endpoint that measures it, the procedure that produces the data, a specimen taken during it, an assessment, and its
result as data, each a class, related by part of, input and output. Then it is explicit that a pharmacokinetic
objective is measured by an endpoint such as maximum concentration, which needs blood samples taken at set times
after the dose. A change in the dosing schedule then also moves the sampling, and if the endpoint is dropped, it is
clear which samples are no longer needed. Such ontologies could be defined for one study, and then evolve across the
studies under one master protocol or one development programme, until they form a shared backbone that the next
study starts from, instead of an empty template.

This does not start from scratch. Community ontologies aligned to the Basic Formal Ontology (BFO) and the Core
Ontology for Biology and Biomedicine (COB) already cover parts of it: OBI for investigations, study designs and assays,
IAO for objectives, plans and data, RO for relations, MAxO for medical actions, MONDO for diseases, and NCIt for
definitions. The principle, from this work and earlier work: reuse them, author only what they lack, and give every
authored class an upstream parent. Making a model precise enough for a machine also finds errors that reading does
not: in the documents here, strata said to be defined in "Core Protocol documents" are defined in PANDA (BP04),
and the Core 4.1 table of contents misses two sections (BP16).

The design modules here are test cases on the way, not that ontology. They anchor their classes in 16 terms from OBI
(with IAO and BFO), MONDO and HP and pass an OWL 2 DL check; no ontologist has reviewed them yet.

## Before this work

Earlier projects pointed in this direction. The EFPIA Smart Program Design team (2013) named the gap: industry standards
do not cover the programme level or the rationale behind design decisions. A volunteer PhUSE project, the Clinical
Development Design (CDD) Framework (2015–2018), sketched ideas for capturing decisions, alternatives not taken and
the evidence behind them ([PhUSE project page](https://advance.hub.phuse.global/wiki/x/byCZAQ);
[Applied Clinical Trials, April 2018](https://www.appliedclinicaltrialsonline.com/view/barriers-and-solutions-smart-clinical-program-designs-0)).
In the same years master protocols came into use, with one programme split into a master and its appendices. The
work here tests the structural part of those ideas on two of them. Besides the ontologies, it needs an authoring
environment design teams will use, and agreed decision and argument patterns. The hard part is getting teams to
state decisions and arguments at the time.
