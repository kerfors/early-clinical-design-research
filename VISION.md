# Where this is heading

Master-protocol templates solve document modularity. What trials actually share and change is design content:
eligibility criteria, arms and doses, endpoints and instruments, schedule cells, allocation rules. No standard today
carries that content as reusable units with one identity across trials and versions, or records who decides what at
which layer.

The idea is design content as modules of components: one identity per component, wherever it occurs; explicit
relations between layers (inherits, delegates, overridable default, restates, extends, overrides); a binding to the
version of the layer a component depends on; and decisions as objects of their own: who decides, at which layer,
bound to what, with which alternatives and arguments.

The future this points to:

1. **Design in the model.** A trial is composed from reusable components with one identity across trials.
2. **Decisions captured where they are made**, with their arguments: the part no public document holds.
3. **Layers as relations, not chapters.** An unanswered delegation is a validation error, not a later finding.
4. **Documents as views.** The Core, DSA and ISA documents and an ICH M11 rendering are generated from the model.
   USDM and M11 become outputs, not mapping targets.
5. **Evolution is native.** An amendment changes a component or a decision, and every user of it is listed, to
   rebind or to stay.

## After components: the ontologies behind the content

Components in a graph are only a first part. Behind the content are classes and relations: an objective, the
endpoint that measures it, the procedure that produces the data, a specimen taken during it, an assessment, and its
result as data, each a class, related by part of, input and output. Then it is explicit that a pharmacokinetic
objective is measured by an endpoint such as maximum concentration, which needs blood samples taken at set times
after the dose. A change in the dosing schedule then also moves the sampling, and if the endpoint is dropped, it is
clear which samples are no longer needed. Such ontologies could be defined for one study, and then evolve across the
studies under one master protocol or one development programme, until they form a shared backbone that the next
study starts from, instead of an empty template.

This does not start from scratch. Community ontologies aligned to the Basic Formal Ontology (BFO) and the Core
Ontology for Biology and Biomedicine (COB) already hold much of it: OBI for investigations, study designs and assays,
IAO for objectives, plans and data, RO for relations, MAxO for medical actions, MONDO for diseases, and NCIt for
definitions. The principle, from this work and earlier work: reuse them, author only what they lack, and give every
authored class an upstream parent. Making a model precise enough for a machine also finds errors that reading does
not, in the documents and in the ontologies reused.

The design modules here are test cases on the way, not that ontology. They anchor their classes in 16 terms from OBI
(with IAO and BFO), MONDO and HP and pass an OWL 2 DL check; no ontologist has reviewed them yet. Published as Linked
Data, with identifiers that resolve as in [m11-rdf](https://w3id.org/m11-rdf/), they would let the questions here be
asked across programmes.

This is the structural part of the 2018 CDD vision, now testable on public material. Besides the ontologies, it needs
an authoring environment design teams will use, and agreed decision and argument patterns. The hard part is getting
teams to state decisions and arguments at the time.
