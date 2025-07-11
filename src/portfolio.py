import pandas as pd
import numpy as np
import yfinance as yf
from scipy.optimize import minimize

class Portfolio:
  def __init__(self, portfolio:list,  lower_bound:float, upper_bound:float):

    self.portfolio = portfolio
    self.weights = None
    self.dfclose = None
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    self.boundfail = False

    if lower_bound >= upper_bound:
      self.boundfail = True

  def get_data(self, period:str=None, start_date:str=None, end_date:str=None):
    """
    Downloads the portfolios adjusted closes either by 'period' or 'start_date' and 'end_date'.
    Only one method of date input should be provided.
    Data downloaded should be big enough to handle calculations.
    """
    try:
      if self.boundfail:
        raise ValueError("Lower bound cannot be greater or equal to upper bound.")

      if period and (start_date or end_date): #checks if both methods of date input are used
        raise ValueError("Provide either 'period' OR both 'start_date' and 'end_date' -- not both.")

      if period:
        period = period.strip()
        self.dfclose = yf.download(self.portfolio, period=period, progress=False, auto_adjust=False)["Adj Close"]
      elif start_date and end_date:
        start_date = start_date.strip()
        end_date = end_date.strip()
        self.dfclose = yf.download(self.portfolio, start=start_date, end=end_date, progress=False, auto_adjust=False)["Adj Close"]
      else:
        raise ValueError("You must provide either a 'period' or both 'start_date' and 'end_date'.")

      if self.dfclose.empty or self.dfclose is None:
        raise ValueError("Downloaded price data is empty or unavailable.")
      elif len(self.dfclose) <= 2: 
        raise ValueError("Downloaded price data is too short.")
      elif len(self.dfclose) < 21: #average trading days in a month
        print("Warning: Limited price history may lead to unreliable metrics.")

      return self.dfclose, None

    except Exception as e:
      return None, str(e)

  def get_weights(self, type_weight:str):
    """
    Returns a list of weights for the portfolio.

    type_weight: Input 'eq' for equal-weighted portfolio or 'opt' for optimized weights based on sharpe-ratio
    """
    try:
      dfclose = self.dfclose
      if dfclose is None or dfclose.empty:
        raise ValueError("The portfolio's price data is missing. Please properly run 'get_data' first.")
      elif len(dfclose) <= 2:
        raise ValueError("Downloaded price data is too short.")

      #Get log returns of each asset
      log_returns = np.log(dfclose/dfclose.shift()).dropna()

      #Calculate initial portfolio metrics
      weights = np.repeat(1/len(self.portfolio), len(self.portfolio))
      expected_returns = log_returns.mean()*252
      port_returns = weights.T @ expected_returns
      cov_matrix = log_returns.cov()*252
      port_vol = np.sqrt(weights.T @ cov_matrix @ weights)
      rf = 0.045

      #Set bounds and constraints for objective function
      bounds = [(self.lower_bound, self.upper_bound) for _ in range(len(self.portfolio))]
      constraints = {"type": "eq", "fun": lambda w: np.sum(w)-1}
      def neg_sharpe(w):
        port_ret = w.T @ expected_returns
        port_std = np.sqrt(w.T @ cov_matrix @ w)
        return -((port_ret - rf)/port_std)

      if type_weight.strip().lower() == "eq":
        self.weights = [float(i) for i in weights]
        if sum(self.weights) > 1:
          raise ValueError("Sum of portfolio weights are greater than 1. Lower bound may be too high.")
      elif type_weight.strip().lower() == "opt":
        optimized_weights = minimize(neg_sharpe, weights, method="SLSQP", bounds=bounds, constraints=constraints)
        self.weights = [round(float(i),4) for i in optimized_weights.x]
      else:
        raise ValueError("Select a valid input for 'type_weight' -- either 'eq' or 'opt'.")
      

      return self.weights, None

    except Exception as e:
      return None, str(e)

if __name__ == "__main__":
    port = Portfolio(["AAPL", "XOM","JPM"], 0.0, 0.5)
    df = port.get_data(period="5y")
    print(df.head())