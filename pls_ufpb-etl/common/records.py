import pandas as pd


def to_mongo_records(df: pd.DataFrame) -> list[dict]:
    """Converte NaN para None de verdade antes de gravar no Mongo.

    `df.where(df.notna(), None)` sozinho NAO basta: numa coluna float64 o
    pandas reinsere None como NaN de volta (o dtype da coluna nao aceita
    o objeto None). O resultado e que valores ausentes viram o double NaN
    dentro do Mongo em vez de null -- e NaN nao e JSON valido, quebra a
    serializacao assim que a API tenta devolver esse campo. astype(object)
    antes do where evita a coercao de volta para NaN.
    """
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")
