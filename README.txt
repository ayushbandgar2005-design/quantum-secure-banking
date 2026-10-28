QUANTUM SECURE BANKING DASHBOARD

Local run:
1. Install Python 3.10+
2. Open a terminal in this folder.
3. Run: pip install -r requirements.txt
4. Run: streamlit run app.py
5. Open the local URL Streamlit prints (usually http://localhost:8501).

Online deployment: upload app.py and requirements.txt to a GitHub repository, then create a Streamlit Community Cloud app using app.py as the entrypoint.

Demo credentials used by the project: ayush / 1234 and admin / 0000. These are intentionally public demo credentials; never use them for real accounts.

Important: this is an educational prototype. Qiskit Aer is a simulator, sample data is synthetic, and payment holds are simulated. Do not use for real banking.
