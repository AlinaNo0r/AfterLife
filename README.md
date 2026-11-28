# AfterLife (Digital Vault)
We all have a digital life, but no one has a digital exit strategy. Building AfterLife: the first smart app that protects your privacy and passes on your digital legacy so you can 'log out' on your own terms.

## 📌 Project Goal:
To engineer a centralized, highly secure web-based ecosystem that automates the inheritance of digital assets, preserves professional and emotional legacies through context-constrained AI-driven communication, and enforces robust security guardrails via inactivity-based background trigger matrices.

### 👀 Problem Statements:
This problem statement breaks down the core vulnerabilities of current systems, directly mapping each issue to a missing component in standard web architectures that our system layout resolves.
* **Lack of Digital Asset Management**
* **Difficulty for Family Members Accessing Accounts**
* **Privacy and Security Risks**
* **Absence of Secure Inheritance Mechanisms**
* **Loss of Emotional Memories and Communication**
* **Lack of Personalized Digital Legacy Solutions**
* **Inactivity Detection Challenges**
* **Need for a Centralized and User-Friendly Platform**
* **Vulnerability of Unencrypted Documents**

### 🔑 Key Features:
* **The Inactivity Tracking Switch:** Deploy an automated background loop that pings user profiles every 3–4 days and activates a 7-day grace period status if missed.
* **The Zero-Knowledge Credential Vault:** Secure account passwords and sensitive text records using browser-to-server cryptography before saving them to disk.
* **The Secure Document Locker:** Provide a web interface supporting the safe ingestion, storage, and isolation of multi-format binary payloads (PDF certificates, financial
records, and images).
* **The AI Digital Twin Persona Chatbot:** Formulate a conversational text portal for verified beneficiaries that restricts all topic outputs to the exact text history provided by the creator.
* **The Milestone Video Vault:** Construct a time-locked queue that calculates release dates using future system timestamps, securely holding data until the active calendar clock matches the release criteria.
* **The Consensus Verification Ring:** Enforce a double-verification rule requiring confirmation from both independent contacts before changing account state flags.
* **The Trusted Circle:** Invite contacts separately as beneficiaries, death witnesses, or both. Each role requires its own explicit acceptance. Assign credentials, memory capsules, and Legacy AI access in their respective sections. The Legacy AI workspace supports beneficiary-specific memory uploads and context.
* **Fail-Closed Witness Quorum:** Require at least two accepted witnesses to confirm death before inactivity-based release. Owners may increase the quorum; it is frozen when warning begins, and inactivity alone never releases assets.

### 🛠️ Technologies Used:
* **Frontend:** HTML, CSS, JAvascript, React
* **Backend:** Python, Django Framework, AP scheduler
* **Database:** PostgreSQL 
* **Cryptography:** Fernet cryptography and APschedular

## Run locally

The React frontend and Django API run in separate terminals. Start PostgreSQL first and make sure the database settings in `FYP/.env` are correct.

1. From the project root, start the Django API:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r .\FYP\requirements.txt -r .\FYP\requirements-legacy-ai.txt
   .\.venv\Scripts\python.exe .\FYP\manage.py migrate
   .\.venv\Scripts\python.exe .\FYP\manage.py runserver 127.0.0.1:8000
   ```

   Trusted Circle invitations need a working email configuration in `FYP/.env` (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, and `FRONTEND_URL`). Credential encryption also requires a valid `FIELD_ENCRYPTION_KEY`; keep it outside source control and do not replace it after storing encrypted credentials.

2. In a second terminal, start the frontend:

   ```powershell
   Set-Location .\frontend
   npm run dev
   ```

3. Open the frontend URL shown by Vite (usually `http://localhost:5173`). Its development proxy forwards API requests to Django on port 8000.

Vault uploads are not served from a public media URL. Released capsules are downloaded through the authenticated beneficiary endpoint, which checks both the accepted beneficiary role and the capsule's release state.

### Legacy AI (prototype)

Legacy AI uses retrieval-augmented generation, not model fine-tuning. Owners can scope PDF, TXT, Markdown, or pasted memories to individual accepted beneficiaries, review a memory-coverage estimate, add relationship-specific context, and privately test a temporary preview before release. A local MiniLM embedding model indexes and searches memories; its model files are downloaded the first time the backend processes an upload.

Response generation uses Ollama on the same computer that runs Django. Install [Ollama for Windows](https://ollama.com/download/windows), open Ollama, then run this in PowerShell once:

```powershell
ollama pull qwen2.5:3b
```

The default model is `qwen2.5:3b` (about 1.9 GB to download); it can be changed with `LEGACY_OLLAMA_MODEL` in `FYP/.env`. Ollama's local API defaults to `http://127.0.0.1:11434` and can be overridden with `LEGACY_OLLAMA_URL`. No hosted AI API key or per-request provider payment is needed. The first model download requires internet; later inference runs locally. Reply speed and quality depend on the laptop, and small local models may produce less capable responses. Check the model's license before use or redistribution.

Selected memory excerpts, relationship/tone context, and messages—including owner preview questions—are processed by the local Ollama model after the owner enables processing; nominee chat additionally requires the beneficiary to accept the notice. Owner previews are temporary and are not saved to beneficiary chat history. Uploaded memory files/chunks and beneficiary chat transcripts are stored in the project's existing database/media storage and this feature does not encrypt them at rest; they are not exposed through a public media URL. The computer/server operator can access local files and database contents, so use only data that is appropriate for the demo and has the necessary consent. Withdrawing consent deletes the stored chat history in this application.

The progress display is a heuristic about the volume, topic coverage, and variety of saved memories; it is not a percentage of model training, a guarantee of personality accuracy, or a mental-health assessment. Legacy AI is a memorial-support tool, not the deceased person, a therapist, or crisis care. Chat is gated on accepted beneficiary access and the existing confirmed release state.

###  ⚙  Development Baseline
* **Processor Engine (CPU):** Minimum 2.0 GHz Quad-core processor (intel core i5, AMD ryzen 5)
* **System RAM:** 8GB or greater to acommodate the local web app and database server simultaneously
* **Persistent Storate Disk Allocation:** Min of 64GB of free storage workspace to hold system boundaries, temporary assets buffer and tracking tables dumps.


## 👥 Team Members & Acknowledgments
### The Team
* **Member 1 Alina Noor** - Reg No: 22-us-770-53 - Roll No: 22BSSE70753 - GitHub Profile: (https://github.com/AlinaNo0r)
* **Member 2 Saima Kousar** - Reg No: 22-us-770-56 - Roll No: 22BSSE70761 - GitHub Profile: (https://github.com/Engineer-Saima)
* **Member 2 Nayyab Khatoon** - Reg No: 22-us-770-54 - Roll No: 22BSSE70754 -  GitHub Profile: (https://github.com/Nayyab713)

### Supervisor
* **Supervisor Name** - Sir Kaleem Ullah

### Acknowledgments
* We express our gratitude to DEPARTMENT OF SOFTWARE ENGINEERING for providing the resources to conduct this project.
* Special thanks to our project supervisor and appreciation to our parents.
* We are also incredibly thankful to our group members and to everyone who assisted, reviewed, or supported us during the technical execution and successful compilation of this project proposal.
