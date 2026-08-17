## Trading Journal

## [Open Live Dashboard](https://andrey-trading-journal.streamlit.app/)

An interactive dashboard for in-depth trading statistics analysis and risk management. The project was built to automate trade tracking, identify profitable/unprofitable patterns, and visualize overall performance.

## Tech Stack
- **Python** - Core logic
- **Pandas** - ETL processes, calculations
- **Plotly** - Interactive data visualization
- **Streamlit** - Web interface
- **PostgreSQL + SQLAlchemy** - Data storage and DB connection

## Interface
<img width="1919" height="905" alt="image" src="https://github.com/user-attachments/assets/6d04d198-5a0a-4b1d-9c88-0b9197c96c97" />
<img width="1919" height="900" alt="image" src="https://github.com/user-attachments/assets/7970565a-a11f-4e56-9a48-8370c8c3c9ff" />
<img width="1919" height="908" alt="image" src="https://github.com/user-attachments/assets/eae902d4-72c3-4df3-b1f6-8d50bfb3a727" />
<img width="1919" height="903" alt="image" src="https://github.com/user-attachments/assets/68cd0ed1-3916-486c-b3b1-d467a2133891" />

## Key Features
- **Full ETL Pipeline** — Scripts clean the raw data, recover missing values where possible, and load everything into a relational PostgreSQL database.
- **Dynamic Filtering** — Filters by asset class (Crypto/RWA), deposit size, years, and months.
- **Equity Analysis** — Plots an equity curve along with a dynamically calculated moving average to assess profitability trends.
- **Statistics Segmentation** — Detailed performance breakdowns across 7 parameters: day of the week, trading session, pattern, setup, position direction (Long/Short), pairs, and counter-trend trades.
- **Performance Extremes** — An algorithm that extracts the best and worst results based on specific metrics, including dynamic outlier protection (requires a minimum number of trades).
- **Emotional Analysis** — Tracks trading mistakes, maps their distribution across trading sessions, and calculates the total cost of mistakes.
- **Advanced Stats & Risk Management** — Built-in Monte Carlo simulation to estimate the probability of passing prop firm challenges, a conversion funnel for accounts, optimal position sizing using the Kelly Criterion, and a heatmap tracking profit by time and day.
