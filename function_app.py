import azure.functions as func
import logging
import os
import json
import pyodbc
from rapidfuzz import process, fuzz

app = func.FunctionApp()

def to_float(value):
    """
    Safely converts a database value to a float, defaulting to 0.0.
    Handles None, empty strings, and other non-numeric values defensively.
    """
    if not value:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

@app.route(route="GetOrderStatusFuzzy", auth_level=func.AuthLevel.FUNCTION)
def GetOrderStatusFuzzy(req: func.HttpRequest) -> func.HttpResponse:
    """
    Looks up a customer's order status using fuzzy name matching.
    This endpoint is secured and requires a function API key.
    It connects to the database using the function's Managed Identity.
    """
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

    db_server = os.environ.get('DB_SERVER')
    db_name = os.environ.get('DB_NAME')

    if not all([db_server, db_name]):
        logging.error("Database connection details (Server, Name) are not fully configured in Application Settings.")
        return func.HttpResponse("Server configuration error.", status_code=500)


    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={db_server};"
        f"DATABASE={db_name};"
        f"Authentication=ActiveDirectoryMsi"
    )
    
    try:
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT CustomerName FROM Orders")
            all_db_names = [row.CustomerName for row in cursor.fetchall()]

            if not all_db_names:
                return func.HttpResponse("No customers found in the database.", status_code=404)

            best_match_tuple = process.extractOne(customer_name_input, all_db_names, scorer=fuzz.WRatio, score_cutoff=75)

            if not best_match_tuple:
                result = {"detail": f"Sorry, I couldn't find an order for a name similar to '{customer_name_input}'."}
                return func.HttpResponse(json.dumps(result), mimetype="application/json", status_code=404)

            best_matched_name = best_match_tuple[0]
            
            # Use SELECT * to get all columns easily
            query_details = "SELECT * FROM Orders WHERE CustomerName = ?"
            cursor.execute(query_details, best_matched_name)
            row = cursor.fetchone()

            if row:
                result = {
                    "version": "4.0",  # <-- OUR UNDENIABLE PROOF
                    "customerName": row.CustomerName,
                    "orderDate": str(row.OrderDate) if row.OrderDate else None,
                    "readyDate": str(row.ReadyDate) if row.ReadyDate else None,
                    "calledDate": str(row.CalledDate) if row.CalledDate else None,
                    "pickupDate": str(row.PickupDate) if row.PickupDate else None,
                    "mountPrice": to_float(row.MountPrice),
                    "boardPrice": to_float(row.BoardPrice),
                    "depositCash": to_float(row.DepositCash),
                    "depositCheck": to_float(row.DepositCheck),
                    "paymentCash": to_float(row.PaymentCash),
                    "paymentCheck": to_float(row.PaymentCheck),
                    "balance": to_float(row.Balance),
                    "lastUpdatedAt": str(row.LastUpdatedAt) if row.LastUpdatedAt else None
                }
                return func.HttpResponse(json.dumps(result, default=str), mimetype="application/json", status_code=200)
            else:
                return func.HttpResponse("Internal error: Matched but failed to retrieve details.", status_code=500)

    except pyodbc.Error as ex:
        # This will catch database-specific errors, like permission denied.
        sqlstate = ex.args[0]
        logging.error(f"DATABASE ERROR. SQLSTATE: {sqlstate}. Message: {ex}")
        # This specific check is useful for diagnosing Managed Identity permission problems.
        if 'Login failed' in str(ex) or 'Cannot open server' in str(ex):
             logging.error("CRITICAL: This may be a Managed Identity permission issue. Verify the function has the 'db_datareader' role in the SQL database.")
        return func.HttpResponse("Failed to connect to or query the database.", status_code=500)
    except Exception as e:
        # This will catch any other unexpected errors.
        logging.error(f"A general error occurred: {e}")
        return func.HttpResponse("An unexpected server error occurred.", status_code=500)