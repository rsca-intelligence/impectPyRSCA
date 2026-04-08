# load packages
import pandas as pd
import re
import requests
from impectPyRSCA.helpers import RateLimitedAPI, ImpectSession, validate_response, unnest_mappings_dict
from .iterations import getIterationsFromHost

######
#
# This function returns a pandas dataframe that contains all squads for a given iteration
#
######


# define function
def getIterationSquads(iteration: int, token: str, session: ImpectSession = ImpectSession()) -> pd.DataFrame:

    # create an instance of RateLimitedAPI
    connection = RateLimitedAPI(session)

    # construct header with access token
    connection.session.headers.update({"Authorization": f"Bearer {token}"})

    return getIterationSquadsFromHost(iteration, connection, "https://api.impect.com")

def getIterationSquadsFromHost(iteration: int, connection: RateLimitedAPI, host: str) -> pd.DataFrame:

    # check input for iteration argument
    if not isinstance(iteration, int):
        raise Exception("Argument 'iteration' must be an integer.")

    # get iterations
    iterations = getIterationsFromHost(connection=connection, host=host)

    # raise exception if provided iteration id doesn't exist
    if iteration not in list(iterations.id):
        raise Exception("The supplied iteration id does not exist. Execution stopped.")

    # get squads
    squads = connection.make_api_request_limited(
        url=f"{host}/v5/customerapi/iterations/{iteration}/squads",
        method="GET"
    )

    # get data from response
    data = validate_response(response=squads, endpoint="Squads")

    # unnest nested IdMapping column
    data = unnest_mappings_dict(data)

    # convert to pandas dataframe
    df = pd.json_normalize(data)

    # fix column names using regex
    df = df.rename(columns=lambda x: re.sub(r"[\._](.)", lambda y: y.group(1).upper(), x))

    # drop idMappings column
    df = df.drop("idMappings", axis=1)

    # keep first entry for skillcorner, heimspiel and wyscout data
    df.skillCornerId = df.skillCornerId.apply(lambda x: x[0] if x else None)
    df.heimSpielId = df.heimSpielId.apply(lambda x: x[0] if x else None)
    df.wyscoutId = df.wyscoutId.apply(lambda x: x[0] if x else None)

    # add iteration id
    df["iterationId"] = iteration

    # merge with competition info
    df = df.merge(
        iterations[["id", "competitionId", "competitionName", "competitionType", "season", "competitionGender"]],
        left_on="iterationId",
        right_on="id",
        how="left",
        suffixes=("", "_iterations")
    )

    # drop duplicate id column from iterations merge
    df = df.drop("id_iterations", axis=1, errors="ignore")

    # fix some column types
    df["iterationId"] = df["iterationId"].astype("Int64")
    df["competitionId"] = df["competitionId"].astype("Int64")
    df["id"] = df["id"].astype("Int64")

    # define desired column order
    order = [
        "iterationId",
        "competitionId",
        "competitionName",
        "competitionType",
        "season",
        "competitionGender",
        "id",
        "name",
        "wyscoutId",
        "heimSpielId",
        "skillCornerId",
        "countryId",
        "type",
        "gender",
        "imageUrl",
        "access",
    ]

    # select only columns that exist (access/type/gender may vary)
    order = [c for c in order if c in df.columns]

    # reorder data
    df = df[order]

    # sort by id
    df = df.sort_values(["id"])

    # return squads
    return df
