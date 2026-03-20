scoped-metric-engine Documentation
=========================================

scoped-metric-engine is a compact orchestration layer for resolving primitive
and derived metrics across canonical scopes, population modes, and simple
aggregation policies.

It delegates domain-specific interpretation to your application code through:

* metric registration (`metric kind`, `family`, and `value_type`)
* primitive fact fetchers by family
* a population resolver (`observed` or `eligible`)
* a Metric Engine adapter for derived metric calculation

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   GETTING_STARTED

.. toctree::
   :maxdepth: 2
   :caption: Concept Guides:

   concepts/metric-model
   concepts/scope-and-population
   concepts/fetching
   concepts/aggregation

.. toctree::
   :maxdepth: 2
   :caption: How-To Guides:

   howto/translate-english-queries
   howto/define-metric-registry
   howto/implement-fetchers
   howto/configure-population
   howto/define-aggregation-policy
   howto/write-metric-adapter

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   reference/api_index

.. toctree::
   :maxdepth: 1
   :caption: Project:

   contributing
   testing
   faq
   changelog
