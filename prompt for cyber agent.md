I need to plan and build an AI cybersecurity application using LangChain/LangGraph ,   
deployable on IBM watsonx.ai. This app protects rural and small businesses   
from three AI-generated threats: phishing emails, Business Email Compromise   
(BEC), and invoice fraud.

\#\# Architecture Overview

The system is a multi-agent orchestration built with LangGraph, where a central orchestrator routes incoming content to one of three specialized sub-agents. “Shared LLM provider with agent-specific prompts and optional model specialization” (IBM watsonx.ai) and a RAG knowledge layer (IBM watsonx.data).

\#\# Agent Structure

Build the following LangChain agents:

1\. \*\*Orchestrator Agent\*\* — classifies incoming content (email, PDF, invoice)   
   and routes to the correct sub-agent using LangGraph StateGraph.

2\. \*\*Phishing Agent\*\* — extracts and analyzes URLs using reputation APIs \+ LLM-based contextual phishing detection and sender domains; integrates with Google Safe Browsing and [urlscan.io](http://urlscan.io/) APIs for real-time threat lookup.

3\. \*\*BEC Agent\*\* — analyzes email tone, urgency signals, and sender behavior drift using LLM reasoning via watsonx.ai , and behavioral anomaly detection based on historical email patterns.

4\. \*\*Invoice Fraud Agent\*\* — extracts invoice fields via OCR (pytesseract), then cross-checks vendor name, bank account number, and invoice amount against the historical vendor record stored in watsonx.data. Flags any bank account change from prior invoices as a Verify trigger (human-in-the-loop).

\#\# Tech Stack

\- \*\*LangGraph\*\* for agent orchestration, tool binding, and RAG chain  
\- \*\*IBM watsonx.ai\*\* as the LLM backend   
\- \*\*IBM watsonx.data\*\* as the structured data layer \+ external vector database for embeddings (vendor records, email baselines, threat signatures)  
\- \*\*pytesseract\*\* for OCR preprocessing of scanned invoices  
\- \*\*Python\*\* as the primary language

\#\# Key Workflows

Input arrives API call, or file upload. The preprocessing layer runs OCR and parsing. The orchestrator classifies and routes. Each sub-agent returns a risk signal. A Risk Scoring Engine aggregates signals into a confidence score. The Action Layer then executes one of three outputs:  
\- \*\*Alert\*\* — notify the user (low-medium risk)  
\- \*\*Block\*\* — quarantine content (high risk)  
\- \*\*Verify\*\* — pause and escalate to human (ambiguous, or any bank account   
  change on an invoice)

All outcomes are logged back to watsonx.data to improve future detection   
(feedback loop).

\#\# Decision Points to Implement

\- Orchestrator routing decision (threat type classification)  
\- Invoice fraud: bank account number changed? → auto-Verify  
\- Risk score threshold crossing → Alert vs Block vs Verify

\#\# Planning Request

Start by generating a project file structure, the key LangChain/LangGraph components   
needed (agents, tools, chains, retrievers), and a step-by-step build plan   
starting with the Invoice Fraud Agent as the MVP. Include how to configure   
the WatsonxLLM integration and connect to watsonx.data as the data layer.  
