import azure.functions as func
import logging
import os
import json
import pyodbc
from rapidfuzz import process, fuzz # Import the fuzzy matching library

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="GetOrderStatusFuzzy")
def GetOrderStatusFuzzy(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Fuzzy Order Status function processed a request.')

    customer_name_input = req.params.get('customer_name')
    if not customer_name_input:
        try:
            req_body = req.get_json()
            customer_name_input = req_body.get('customer_name')
        except (ValueError, AttributeError):
            return func.HttpResponse("Request body is not valid JSON.", status_code=400)

    if not customer_name_input:
        return func.HttpResponse(
             "Please pass a 'customer_name' in the query string or request body.",
             status_code=400
        )

    # Securely get connection details from Application Settings
    db_server = os.environ.get('DB_SERVER')
    db_name = os.environ.get('DB_NAME')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')

    if not all([db_server, db_name, db_user, db_password]):
        logging.error("Database connection details are not fully configured.")
        return func.HttpResponse("Server configuration error.", status_code=500)

    conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={db_password}"
    
    try:
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cursor = conn.cursor()
            
            # --- FUZZY MATCHING LOGIC ---
            cursor.execute("SELECT CustomerName FROM Orders")
            all_db_names = [row.CustomerName for row in cursor.fetchall()]

            if not all_db_names:
                return func.HttpResponse("No customers found in the database.", status_code=404)

            best_match_tuple = process.extractOne(customer_name_input, all_db_names, scorer=fuzz.WRatio, score_cutoff=75)

            if not best_match_tuple:
                logging.info(f"No close match found for '{customer_name_input}'.")
                result = {"detail": f"Sorry, I couldn't find an order for a name similar to '{customer_name_input}'."}
                return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=404)

            best_matched_name = best_match_tuple[0]
            
            # --- GET DETAILS FOR BEST MATCH ---
            query_details = "SELECT CustomerName, OrderDate, ReadyDate, Balance FROM Orders WHERE CustomerName = ?"
            cursor.execute(query_details, best_matched_name)
            row = cursor.fetchone()

            if row:
                result = {
                    "customerName": row.CustomerName,
                    "orderDate": str(row.OrderDate) if row.OrderDate else "N/A",
                    "readyDate": str(row.ReadyDate) if row.ReadyDate else "Pending",
                    "balance": float(row.Balance)
                }
                return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=200)
            else:
                return func.HttpResponse("Internal error: Matched but failed to retrieve details.", status_code=500)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse("Failed to connect to or query the database.", status_code=500)
    