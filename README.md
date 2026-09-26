*Read this in [Russian](README_RU.md)*

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
<img width="1919" height="899" alt="image" src="https://github.com/user-attachments/assets/fd308125-34a7-4faa-86b9-3dfe56ad4a47" />
<img width="1919" height="913" alt="image" src="https://github.com/user-attachments/assets/0823dedc-f4f3-4df8-8223-e4bb20c1160a" />
<img width="1919" height="908" alt="image" src="https://github.com/user-attachments/assets/b76e4309-f97a-44df-872b-6cccd9b55ce5" />
<img width="1919" height="905" alt="image" src="https://github.com/user-attachments/assets/16dea7f5-b054-41c5-8f4f-1aacf7371957" />

## Key Features
- **Full ETL Pipeline** — Scripts clean the raw data, recover missing values where possible, and load everything into a relational PostgreSQL database.
- **Dynamic Filtering** — Filters by asset class (Crypto/RWA), deposit size, years, and months.
- **Equity Analysis** — Plots an equity curve along with a dynamically calculated moving average to assess profitability trends.
- **Statistics Segmentation** — Detailed performance breakdowns across 7 parameters: day of the week, trading session, pattern, setup, position direction (Long/Short), pairs, and counter-trend trades.
- **Performance Extremes** — An algorithm that extracts the best and worst results based on specific metrics, including dynamic outlier protection (requires a minimum number of trades).
- **Emotional Analysis** — Tracks trading mistakes, maps their distribution across trading sessions, and calculates the total cost of mistakes.
- **Advanced Stats & Risk Management** — Built-in Monte Carlo simulation to estimate the probability of passing prop firm challenges, a conversion funnel for accounts, optimal position sizing using the Kelly Criterion, and a heatmap tracking profit by time and day.
