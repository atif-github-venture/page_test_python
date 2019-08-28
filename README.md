# page_test_python

Type of Test:
Page Performance Test

Implementation Language:
Python

Libraries:
•	Browsermob proxy
•	Haralyzer
•	JSON, OS
•	Selenium
•	Chartify
•	Panda, etc

Idea:
•	To enable a quick feedback loop in ATCICD closer to development pipeline or scheduled nightly builds, for performance per page.
•	The test is built to use meta data (json) and no coding needed to included more scenarios.
•	The preset expected response time can be used to measure against the actual response time with threshold passed per test.
•	This also generates a custom build graph grouping actual Vs expected per API

Yet to be implemented:
o	Comparing for pass fail per API
o	Push results to manta/elasticsearch
o	Any further enhancement to make the solution better and globally useful agnostic to projects
