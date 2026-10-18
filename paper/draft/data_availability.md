# Data Availability

The code and the raw campaign data, including persisted trace spans and the reconstructed
dependency graphs, are available together with the analysis outputs at
https://github.com/Daxx133-bot/proj-1-updated and will be archived at Zenodo (DOI: [TO FILL]). The experiments used DeathStarBench at upstream commit 6ecb097 %[id:dsb_commit]. The Locust
workloads are defined in `infra/_locustfile_baseline.py` for Social Network and
`infra/_locustfile_hotel.py` for Hotel Reservation. Code is
released under the MIT licence; data and figures are released under CC BY 4.0. Running
`python paper/build_all.py` rebuilds every reported value from the logged data.
