# AI Agent Tool: A Secure, Serverless Database Connector

This repository contains a production-ready, serverless microservice built with Python and deployed as an Azure Function. It was developed as a key component of a full-stack AI business website to solve a critical problem: **how to give an AI Agent secure, real-time access to a private database.**

This function serves as a specialized "tool" that an Azure AI Agent can call. It enables the agent to perform typo-tolerant customer order lookups, demonstrating a practical application of combining AI with traditional data systems.

---

## Architectural Role & Problem Solved

In the larger application, this function acts as a secure bridge between the AI and the data.

1.  A user asks the AI Agent for an order status.
2.  The AI Agent determines it needs to use its `GetOrderStatusFuzzy` tool.
3.  The agent calls this Azure Function's secure HTTP endpoint, passing the customer's name.
4.  This function connects to the database, performs the fuzzy search, and returns a clean, anonymized JSON payload.
5.  The AI Agent uses this data to formulate its final response to the user.

This decoupled architecture solves a major security challenge by ensuring the AI's conversational logic is completely isolated from the sensitive database connection credentials and logic.

---

## Key Features & Technical Highlights

-   ### Typo-Tolerant Search (Fuzzy Matching)
    Implements the `rapidfuzz` library (`fuzz.WRatio`) to intelligently find customer names even with common spelling errors. This dramatically improves the user experience by reducing "user not found" failures and making the AI appear more intelligent and helpful.

-   ### Passwordless Security (Managed Identity)
    The function authenticates to the Azure SQL Database using its own Azure Active Directory **Managed Identity**. This is a modern, best-practice approach that **completely eliminates database credentials** from the application's code and configuration. This design choice significantly hardens the application's security posture against credential theft.

-   ### Proactive Data Privacy
    Before returning data to the AI, it anonymizes the customer's last name (e.g., "Jane Doe" -> "Jane D."). This adheres to the principle of least privilege, ensuring the AI agent only receives the data it absolutely needs for its task and protecting customer privacy by default.

-   ### Serverless & Cost-Efficient
    Built on the Azure Functions Consumption Plan, the application only incurs costs when it is actively processing a request, making it an extremely cost-effective solution for a public-facing application with variable traffic.

---

## Technology Stack

| Category          | Technology / Service                      | Purpose                                       |
|-------------------|-------------------------------------------|-----------------------------------------------|
| **Cloud Platform**  | Microsoft Azure                           | Hosting, Security, and AI Services            |
| **Core Service**    | Azure Functions                           | Serverless, event-driven compute              |
| **Language**        | Python 3.11                               | Backend logic and data processing             |
| **Database**        | Azure SQL Database                        | Storing structured customer order data        |
| **Authentication**  | Azure Active Directory (Managed Identity) | Secure, passwordless service-to-service auth  |
| **Key Libraries**   | `pyodbc`, `rapidfuzz`                     | Database connectivity and fuzzy string matching |

---

## Running Locally

To run this project for local development, the [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local) are required.

1.  Clone the repository.
2.  Set up a Python virtual environment and run `pip install -r requirements.txt`.
3.  Create a `local.settings.json` file in the project root. **This file is git-ignored and must not be committed to source control.** For local testing, you would typically use a standard username/password connection string, as Managed Identity is an Azure-native feature that only works when deployed.
