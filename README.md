Project Summary: QR Code Support Application for Vehicles
Objective
Develop a web application that allows operators to quickly report a problem with a vehicle by scanning a QR code affixed to it. The goal is to simplify support request transmission, ensure that essential vehicle information is automatically recorded, and reduce downtime.
How It Works
QR Code on Each Vehicle
	• Each vehicle has a unique QR code.
	• The QR encodes a short URL linked to the vehicle’s serial number and type.
Operator Experience
	• The operator scans the QR code with their smartphone.
	• A support form opens, already pre-filled with the vehicle information.
	• The operator enters their name, phone number, and a short description of the problem.
	• Upon submission, the system records the request and sends an email to the dedicated support address.
Admin Features
	• Secure admin portal (not accessible to operators).
	• Creation and management of vehicles with QR code generation (individual or batch).
	• Ticket export, QR code regeneration, submission tracking.
Benefits
	• Faster issue reporting (scan → form → submit).
	• Automatic vehicle identification (reduces input errors).
	• Centralized registry of support requests with email notifications.
	• Scalable: easy to add new vehicles.
	• Future-proof: can later integrate with ticketing tools like ClickUp, Jira, or ServiceNow.
Scope of the Light Version (MVP)
	• Secure web application (FastAPI, PostgreSQL, Python stack).
	• Generation of unique vehicle-linked QR codes.
	• Bilingual support form (FR/EN) pre-filled with vehicle details.
	• Email notifications sent upon submission.
	• Basic admin console for vehicle and ticket management.
	• Basic security (TLS, rate limiting, action logging).
Estimated Effort
Approx. 150 hours for development, testing, and deployment of the first functional version.
This estimate includes:
	• Python/SQL for the web application.
	• Development of admin tools.
	• Configuration of security, email, and QR code printing flows.
Documentation and deployment environment setup.<img width="1059" height="1100" alt="image" src="https://github.com/user-attachments/assets/d518db7e-0ba8-4f96-880f-140b51318cc7" />
