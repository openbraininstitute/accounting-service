# accounting-service

## Description

This service is composed by:

-   `accounting-service`: main service.

## Local build and deployment

Requirements:

- [Docker compose](https://docs.docker.com/compose/) >= 2.24.4
- [uv](https://docs.astral.sh/uv/)

Valid `make` targets:

```
help                    Show this help
install                 Install dependencies into .venv
compile-deps            Create or update the lock file, without upgrading the version of the dependencies
upgrade-deps            Create or update the lock file, using the latest version of the dependencies
check-deps              Check that the dependencies in the existing lock file are valid
lint                    Run linters
build                   Build the docker images
run                     Run the application in docker
kill                    Take down the application and remove the volumes
clean                   Take down the application and remove the volumes and the images
test                    Run tests in docker
test-local              Run tests locally
migration               Create the alembic migration
show-config             Show the docker-compose configuration in the current environment
sh                      Run a shell in the app container
```

To build and start the Docker images locally, you can execute:

```bash
make run
```


## Remote deployment

To make a release, build and publish the Docker image to the registry, you need to:

-   create a release through the GitHub UI (recommended), or
-   push a tag to the main branch using git.

The format of the tag should be `YYYY.M.N`, where:

-   `YYYY` is the full year (2024, 2025 ...)
-   `M` is the short month, not zero-padded (1, 2 ... 11, 12)
-   `N` is any incremental number, not zero-padded (it doesn't need to be the day number)


## Documentation

The API documentation is available locally at <http://127.0.0.1:8100/docs> after the local deployment.

## High level overview

The accounting service needs to be initialised with prices for each of the actions that a user can do which incur some costs that have to be tracked. To define a price, the /price endpoint is used. There are 3 major price types: oneshot, longrun and storage. Also a subtype like ml-llm or ml-rag has to be specified. Note that at the moment, the subtypes are a list of constants which have to be kept in sync across some components:

* [The ServiceSubType enum in core-web-app/src/types/accounting/index.ts](https://github.com/openbraininstitute/core-web-app/blob/0b81e07d8f2de6996116d61ea8bc31829e3f0e07/src/types/accounting/index.ts#L39C13-L39C27)
* [The JobSubType enum in virtual-lab-api/virtual_labs/external/accounting/models.py](https://github.com/openbraininstitute/virtual-lab-api/blob/d1e6b9c9b7adca42ceb24b3302c5c599cfa283d2/virtual_labs/external/accounting/models.py#L92)
* [The ServiceSubtype class in accounting-sdk/src/obp_accounting_sdk/constants.py](https://github.com/openbraininstitute/accounting-sdk/blob/577483ee62e134a0d52a381aeead8404846e0ff0/src/obp_accounting_sdk/constants.py#L33)

To define prices, you also need to specify a 'valid from' timestamp, a 'valid to' timestamp (which can be null for indefinitely), a fixed cost and a multiplier.

The accounting service needs to know which virtual labs and projects exist. This is done by the virtual-lab-api component, which calls the following endpoints:

* /account/virtual-lab endpoint with the ID and the name of the virtual lab.
* /account/project endpoint with the ID of the virtual lab, the ID of the project and the name of the project in the format 'virtuallabname/projectname'.

Once the virtual labs and projects exist in the database of the accounting service, then it's possible to set up some budgets. First, the virtual lab needs to top up its credits: when the user has bought credits (the payment is handled by the virtual-lab-api, not by this accounting service), then virtual-lab-api will call the /budget/top-up endpoint with a virtual lab ID and an amount of credits. Afterwards, the /budget/assign endpoint can be used to assign a part or all of the credits of the virtual lab to a specific project. The required parameters are the IDs of the virtual lab and project, and the number of credits.

Once a user has assigned some budget to a project, then he/she can start spending those credits. First credit has to be reserved with either /reservation/oneshot or /reservation/longrun. The service will return a unique job ID. If needed, a reservation can be deleted with a http DELETE call. 

The job ID which was returned during the reservation call, is needed when submitting the actual usage. Actions with a fixed cost need just one call to /usage/oneshot. Long running tasks need several calls to  /usage/longrun, with a status such as STARTED, RUNNING or FINISHED. You also need to specify the type, subtype, project, job ID, an optional name, an amount and a timestamp.

## Funding & Acknowledgment
 
The development of this software was supported by funding to the Blue Brain Project, a research center of the École polytechnique fédérale de Lausanne (EPFL), from the Swiss government's ETH Board of the Swiss Federal Institutes of Technology.
 
Copyright © 2024 Blue Brain Project/EPFL
Copyright © 2025 Open Brain Institute
