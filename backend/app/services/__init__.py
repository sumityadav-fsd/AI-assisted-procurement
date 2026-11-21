"""Orchestration layer. OWNER: Member 2.

Services are the only code that may combine ai + document + procurement + database:

    api (thin) -> services -> document (extract) -> ai (structure) -> procurement (compute) -> database

Nothing else crosses these boundaries. Not implemented yet.
"""
