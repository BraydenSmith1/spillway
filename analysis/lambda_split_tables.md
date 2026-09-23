## Oversupply vs congestion: fleet, Sep 2025 – Jul 2026

| fuel   | cause      |   curt_gwh |   pct_of_fuel |   value_at_node_musd |   value_at_lambda_musd |
|:-------|:-----------|-----------:|--------------:|---------------------:|-----------------------:|
| PVGR   | congestion |       2991 |          70.7 |               -36.91 |                  56.01 |
| PVGR   | oversupply |       1106 |          26.1 |               -10.56 |                  -5.49 |
| PVGR   | other      |        136 |           3.2 |                 1.56 |                   3.3  |
| WIND   | congestion |       4302 |          84   |               -52.92 |                 102.74 |
| WIND   | oversupply |        554 |          10.8 |                -8.59 |                  -2.77 |
| WIND   | other      |        263 |           5.1 |                 1.09 |                   5.92 |

## By month (solar + wind), share of curtailed MWh by cause

| month   |   curt_gwh |   oversupply_pct |   congestion_pct |   other_pct |   avg_lambda_when_curtailed |
|:--------|-----------:|-----------------:|-----------------:|------------:|----------------------------:|
| 2025-09 |        229 |            nan   |             89.4 |        10.6 |                       32.71 |
| 2025-10 |        711 |             18.7 |             76.5 |         4.8 |                       20.25 |
| 2025-11 |        764 |             22.3 |             71.3 |         6.4 |                       18.28 |
| 2025-12 |        790 |              9.1 |             86.1 |         4.7 |                       21.9  |
| 2026-01 |        981 |             46.8 |             49.4 |         3.8 |                       14.79 |
| 2026-02 |       1259 |             43.9 |             53   |         3.1 |                        4.46 |
| 2026-03 |       1621 |             12.4 |             85   |         2.6 |                       15.35 |
| 2026-04 |       1380 |              0.4 |             96.4 |         3.2 |                       28.28 |
| 2026-05 |        664 |             10.2 |             84.1 |         5.6 |                       19.27 |
| 2026-06 |        881 |            nan   |             95.2 |         4.8 |                       23.12 |
| 2026-07 |         71 |            nan   |             84.8 |        15.2 |                       22.98 |

## Top 50 solar sites

| resource          | node         | county    | owner                                   |   curt_gwh |   oversupply_pct |   congestion_pct |   other_pct |   avg_congestion_usd_mwh |   avg_lambda_usd_mwh |
|:------------------|:-------------|:----------|:----------------------------------------|-----------:|-----------------:|-----------------:|------------:|-------------------------:|---------------------:|
| GALLOWAY_SOLAR1   | GALO_RN1     | Concho    | 225DD 8me LLC                           |      127.1 |             25.8 |             73.6 |         0.6 |                   -17.25 |                10.46 |
| REDBARN_UNIT_1    | REDBARN_RN   |           |                                         |      114.8 |             21.8 |             77.2 |         1   |                   -18.46 |                12.41 |
| SPTX12B_UNIT1     | SPTX12B_RN   | Upton     | RWE Clean Energy                        |      108.5 |             17   |             79.6 |         3.4 |                   -17.44 |                14.38 |
| WAYMARK_UNIT1     | WAYMARK_RN   |           |                                         |      105.7 |             21   |             71.5 |         7.5 |                   -17.79 |                12.53 |
| CMPD_SLR_SOLAR2   | CMPD_SLR_RN  |           |                                         |      103.3 |              6.5 |             93.5 |         0   |                   -59.52 |                21.24 |
| RIGGINS_UNIT1     | RIGGIN_UNIT1 |           |                                         |       95.1 |             20   |             76.1 |         3.9 |                   -15.05 |                12.32 |
| MISAE_UNIT1       | MISAE_GEN_RN | Childress | Childress Solar Park LLC                |       95   |             13.6 |             80.8 |         5.6 |                   -22.35 |                15.64 |
| CMPD_SLR_SOLAR1   | CMPD_SLR_RN  |           |                                         |       94.7 |              6.8 |             93.2 |         0   |                   -59.43 |                21.12 |
| MISAE_UNIT2       | MISAE_GEN_RN | Childress | Childress Solar Park LLC                |       92.7 |             13.7 |             81   |         5.3 |                   -22.7  |                15.75 |
| ASCK_SLR_SOLAR2   | ASCK_SLR_RN  |           |                                         |       87.3 |              6.2 |             93.8 |         0   |                   -62.75 |                24.67 |
| ASCK_SLR_SOLAR1   | ASCK_SLR_RN  |           |                                         |       85.9 |              6.4 |             93.6 |         0   |                   -62.72 |                24.68 |
| JADE_SLR_UNIT2    | JADE_SLR_ALL | Scurry    | Intersect USA, LLC                      |       83.4 |             16.3 |             82.2 |         1.5 |                   -26.97 |                16.29 |
| GREASWOD_UNIT2    | GREASWOD_ALL | Pecos     | Concho Bluff LLC                        |       79.3 |             18.4 |             71.6 |        10   |                   -18.25 |                13.69 |
| ARAGORN_UNIT1     | ARAGORN_RN   | Culberson | SE Aragorn, LLC                         |       76.3 |             23.4 |             72.3 |         4.3 |                   -13.91 |                11.83 |
| PROSPERO_UNIT1    | PROSPERO_ALL | Andrews   | Prospero Energy Project, LLC (Longroad) |       75.8 |             21.7 |             78.3 |         0   |                   -16.7  |                13.15 |
| JADE_SLR_UNIT1    | JADE_SLR_ALL | Scurry    | Intersect USA, LLC                      |       75.6 |             16.5 |             82   |         1.6 |                   -26.92 |                16.28 |
| PROSPERO_UNIT2    | PROSPERO_ALL | Andrews   | Prospero Energy Project, LLC (Longroad) |       74.4 |             21.2 |             78.7 |         0   |                   -16.8  |                13.33 |
| RAMBLER_UNIT1     | RAMBLER_UNIT | Tom Green | RE Rambler, LLC                         |       70.5 |             25.3 |             73   |         1.7 |                   -17.02 |                 9.88 |
| GALLOWAY_SOLAR2   | GALO_RN1     | Concho    | 225DD 8me LLC                           |       69.8 |             23.3 |             72.3 |         4.4 |                   -17.67 |                11.14 |
| AZURE_SOLAR2      | AZURE_RN     |           |                                         |       68.5 |             18.8 |             81.2 |         0   |                   -24.53 |                13.96 |
| PORT_SLR_UNIT1    | PORTSL_UNIT1 | Denton    | Porter Solar, LLC                       |       64.4 |             26.1 |             67.8 |         6.1 |                   -16.82 |                 8.65 |
| GREASWOD_UNIT1    | GREASWOD_ALL | Pecos     | Concho Bluff LLC                        |       64.1 |             17.3 |             73.1 |         9.5 |                   -18.47 |                14.27 |
| TAYGETE_UNIT2     | TAYGETE_ALL  | Pecos     | West Texas Solar Project II LLC         |       62.5 |             21.8 |             78.2 |         0   |                   -15.96 |                12.72 |
| PHOEBE_UNIT2      | PHOEBE_ALL   | Winkler   | Phoebe Energy Project, LLC              |       61.1 |             26.7 |             70.7 |         2.7 |                   -12.68 |                 9.6  |
| LAPETUS_UNIT_1    | LAPETUS_U1   | Andrews   | Lapetus Energy Project, LLC             |       60.8 |             19.8 |             77.6 |         2.6 |                   -15.27 |                12.63 |
| TAYGETE_UNIT1     | TAYGETE_ALL  | Pecos     | West Texas Solar Project II LLC         |       60.1 |             22   |             78   |         0   |                   -15.84 |                12.6  |
| PHOEBE_UNIT1      | PHOEBE_ALL   | Winkler   | Phoebe Energy Project, LLC              |       59.7 |             26.4 |             71   |         2.6 |                   -12.86 |                 9.76 |
| LGDRAW_S_UNIT1_2  | LGDRAW_S_ALL | Borden    | Engie Longdraw Solar LLC                |       54.6 |             21.6 |             78.4 |         0   |                   -21.57 |                13.62 |
| OBERON_UNIT_1_J01 | OBERON_U1    | Ector     | TotalEnergies                           |       50.3 |             24.1 |             73.4 |         2.5 |                   -13.31 |                11.07 |
| CASL_GAP_UNIT1    | CASL_GAP_UN1 | Upton     | Upton County Solar 2 LLC                |       48.5 |             22.1 |             77.9 |         0   |                   -19.93 |                14.37 |
| FILESSLR_PV1      | FILESSLR_PV1 |           |                                         |       46.3 |              6.3 |             93.7 |         0   |                   -62.08 |                22.94 |
| LGDRAW_S_UNIT1_1  | LGDRAW_S_ALL | Borden    | Engie Longdraw Solar LLC                |       42.4 |             21.5 |             78.4 |         0   |                   -21.62 |                13.68 |
| ANDMDSLR_UNIT2    | ANDMDSLR_ALL | Scurry    | Intersect USA, LLC                      |       37.6 |             23.6 |             76.4 |         0   |                   -33.39 |                15.9  |
| CORAZON_UNIT1     | CORAZON_RN   |           |                                         |       36.6 |             19.2 |             80.8 |         0   |                   -38.32 |                17.41 |
| IMPACT_UNIT1      | IMP_RN1      | Lamar     | Impact Solar 1, LLC                     |       35.4 |             44.8 |             49.5 |         5.6 |                    -6.15 |                 2.27 |
| MCLNSLR_UNIT1     | MCLNSLR_RN   |           |                                         |       34.1 |             44.4 |             51.3 |         4.3 |                   -10.03 |                 4.68 |
| ANDMDSLR_UNIT1    | ANDMDSLR_ALL | Scurry    | Intersect USA, LLC                      |       32.6 |             23.4 |             76.6 |         0   |                   -33.6  |                16.12 |
| AZURE_SOLAR1      | AZURE_RN     |           |                                         |       32.6 |             19.5 |             80.5 |         0   |                   -24.21 |                13.64 |
| MERCURY_PV1       | MERCURY_ALL  |           |                                         |       32.4 |              9.9 |             90.1 |         0   |                   -58.12 |                17.03 |
| JUNO_UNIT2        | JUNO_ALL     | Borden    | SE Juno, LLC                            |       32   |             22.3 |             77.7 |         0   |                   -27.16 |                15.2  |
| MERCURY_PV2       | MERCURY_ALL  |           |                                         |       31.7 |              9.9 |             90.1 |         0   |                   -58.23 |                17.13 |
| JUNO_UNIT1        | JUNO_ALL     | Borden    | SE Juno, LLC                            |       30.2 |             26.4 |             73.6 |         0   |                   -27.3  |                13.39 |
| TAYGETE2_UNIT1    | TAYGETE2_ALL | Pecos     | West Texas Solar Project II LLC         |       30.1 |             25.4 |             74.6 |         0   |                   -16.71 |                12.18 |
| TI_SOLAR_UNIT1    | TI_SOLAR_ALL |           |                                         |       29.3 |             29.1 |             70.9 |         0   |                   -17.3  |                12.3  |
| TAYGETE2_UNIT2    | TAYGETE2_ALL | Pecos     | West Texas Solar Project II LLC         |       28.5 |             25.9 |             74.1 |         0   |                   -16.42 |                11.91 |
| QUEEN_SL_SOLAR1   | QUEEN_SL_RN  |           |                                         |       27.8 |             18.6 |             81.4 |         0   |                   -20.65 |                14.36 |
| ROSELAND_SOLAR1   | ROSELAND_ALL |           |                                         |       27.7 |             37   |             61.7 |         1.2 |                   -20.21 |                10.48 |
| JAY_UNIT2         | JAY_RN_1     |           |                                         |       27.4 |             61.7 |             28.3 |        10   |                    -5.9  |                 2.39 |
| QUEEN_SL_SOLAR2   | QUEEN_SL_RN  |           |                                         |       26.9 |             19.4 |             80.6 |         0   |                   -20.4  |                14.16 |
| EUNICE_PV2        | EUNICE_ALL   |           |                                         |       26.8 |             23.7 |             75.3 |         1   |                   -22.01 |                15.27 |

## Top 20 wind sites

| resource          | node         | county   | owner                          |   curt_gwh |   oversupply_pct |   congestion_pct |   other_pct |   avg_congestion_usd_mwh |   avg_lambda_usd_mwh |
|:------------------|:-------------|:---------|:-------------------------------|-----------:|-----------------:|-----------------:|------------:|-------------------------:|---------------------:|
| HRFDWIND_JRDWIND2 | HRFDWIND_ALL |          |                                |      190.8 |              6.6 |             88.2 |         5.2 |                   -29.02 |                22.94 |
| HRFDWIND_JRDWIND1 | HRFDWIND_ALL |          |                                |      190   |              6.6 |             88.5 |         4.9 |                   -29.02 |                22.91 |
| SHANNONW_UNIT_1   | SHANNONW_RN  | Clay     | 1370 Shannon LLC               |      185.8 |             12.4 |             84.6 |         3   |                   -23.5  |                15.5  |
| SRWE1_UNIT1       | SRWE1_UNIT1  | Borden   | Starwood Energy Group Global   |      139.9 |             12.8 |             79.4 |         7.8 |                   -22.59 |                16.33 |
| SRWE1_SRWE2       | SRWE1_UNIT1  | Borden   | Starwood Energy Group Global   |      138.5 |             11.5 |             80.8 |         7.6 |                   -23.07 |                16.89 |
| MIAM1_G2          | MIAM1_G1_G2  | Roberts  | Invenergy Services LLC         |      133.8 |              9.4 |             90.6 |         0   |                   -25.87 |                18.38 |
| MIAM1_G1          | MIAM1_G1_G2  | Roberts  | Invenergy Services LLC         |      133.8 |              9.4 |             90.6 |         0   |                   -26.15 |                18.67 |
| MWEC_G1           | MWEC_G1      | Dickens  | Invenergy Services LLC         |      132.2 |              9.4 |             66.7 |        23.9 |                   -20.23 |                15.91 |
| INDL_INADALE2     | IND_INADALE1 | Nolan    | RWE Clean Energy               |      130.7 |              9.3 |             63.6 |        27.1 |                   -21.45 |                17.15 |
| INDL_INADALE1     | IND_INADALE1 | Nolan    | RWE Clean Energy               |      119.2 |              9.3 |             63.2 |        27.5 |                   -21.31 |                17.08 |
| SSPURTWO_SS3WIND2 | SSPURT_WIND1 |          |                                |      117.6 |              5.7 |             89.3 |         5   |                   -27.26 |                21.84 |
| SSPURTWO_SS3WIND1 | SSPURT_WIND1 |          |                                |      113.4 |              5.7 |             89.3 |         5   |                   -27.1  |                21.7  |
| PENA_UNIT1        | PENA_ALL     |          |                                |      109.9 |              7.2 |             92.7 |         0.1 |                   -34.62 |                28.54 |
| TKWSW1_ROSCOE     | TKWSW_CHAMP  |          |                                |      109.2 |             10.9 |             75.6 |        13.5 |                   -22.46 |                16.66 |
| BORDAS_JAVEL20    | BORDAS_345   | Webb     | Javelina Wind Energy, LLC      |      105.7 |              7.1 |             90.6 |         2.3 |                   -40.98 |                28.26 |
| GPASTURE_WIND_I   | GPASTURE_ALL | Baylor   | Acciona Energy USA Global, LLC |       94.4 |             11.5 |             88.5 |         0   |                   -23.92 |                16.32 |
| LV3_UNIT_1        | LV3_RN       |          |                                |       94   |             11   |             73.4 |        15.6 |                   -33.96 |                23.88 |
| TKWSW1_ROSCOE2A   | TKWSW_CHAMP  |          |                                |       91.1 |             10.7 |             75.8 |        13.4 |                   -22.71 |                16.84 |
| TTWEC_G1          | TTWEC_G1     | Nolan    | Invenergy Services LLC         |       87.5 |             13.7 |             83.2 |         3.1 |                   -23.38 |                15.45 |
| ROUTE_66_WIND1    | ROUTE66_RN   | Carson   | Onward Energy                  |       86.8 |             11.2 |             88.7 |         0   |                   -32.62 |                21.53 |

## Site x month (top sites), % congestion

| resource          |   2025-09 |   2025-10 |   2025-11 |   2025-12 |   2026-01 |   2026-02 |   2026-03 |   2026-04 |   2026-05 |   2026-06 |   2026-07 |
|:------------------|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|----------:|
| GALLOWAY_SOLAR1   |       100 |        67 |        53 |        74 |        26 |        47 |        83 |        97 |        88 |        99 |        96 |
| REDBARN_UNIT_1    |        91 |        83 |        71 |        78 |        33 |        44 |        84 |        97 |        90 |       100 |        98 |
| SPTX12B_UNIT1     |        83 |        78 |        65 |        76 |        39 |        49 |        82 |        96 |        85 |        98 |        96 |
| WAYMARK_UNIT1     |        55 |        75 |        61 |        67 |        32 |        41 |        76 |        92 |        86 |        95 |        90 |
| CMPD_SLR_SOLAR2   |       100 |        99 |        77 |        91 |        41 |        74 |        88 |        99 |        78 |       100 |       100 |
| RIGGINS_UNIT1     |        74 |        77 |        59 |        75 |        33 |        45 |        81 |        95 |        83 |        98 |        84 |
| MISAE_UNIT1       |        74 |        68 |        77 |        86 |        49 |        56 |        82 |        95 |        92 |        95 |        84 |
| CMPD_SLR_SOLAR1   |       100 |        99 |        77 |        91 |        28 |        74 |        88 |        99 |        78 |       100 |       nan |
| MISAE_UNIT2       |        77 |        68 |        77 |        87 |        48 |        55 |        82 |        96 |        92 |        96 |        85 |
| ASCK_SLR_SOLAR2   |       100 |        96 |        79 |        86 |        56 |        95 |        89 |       100 |        91 |       100 |       100 |
| ASCK_SLR_SOLAR1   |       100 |        95 |        79 |        86 |        56 |        95 |        89 |       100 |        91 |       100 |       100 |
| JADE_SLR_UNIT2    |        48 |        72 |        65 |        84 |        39 |        53 |        87 |       100 |        91 |       100 |       100 |
| HRFDWIND_JRDWIND2 |        89 |        88 |        88 |        94 |        83 |        72 |        90 |        96 |        86 |        95 |        80 |
| HRFDWIND_JRDWIND1 |        88 |        88 |        89 |        94 |        83 |        72 |        90 |        96 |        86 |        95 |        80 |
| SHANNONW_UNIT_1   |       nan |        78 |        83 |        93 |        63 |        74 |        86 |        98 |        85 |        95 |        89 |
| SRWE1_UNIT1       |        77 |        54 |        67 |        84 |        39 |        65 |        91 |        97 |        89 |        95 |        95 |
| SRWE1_SRWE2       |        78 |        55 |        68 |        84 |        36 |        64 |        91 |        97 |        89 |        95 |        95 |
| MIAM1_G2          |       100 |        86 |        91 |        97 |        84 |        71 |        91 |        99 |        91 |       100 |       100 |
