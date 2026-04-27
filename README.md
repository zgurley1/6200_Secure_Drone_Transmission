# Secure Drone Command Communication System

Group: Elis Claros, Bogdan Gerasymenko, Zachary Gurley

## Overview

This project simulates a ground controller communicating with a drone over a TCP socket, 
and demonstrates both the vulnerabilities of an unprotected communication channel and the effectiveness of a properly implemented security protocol. 

This project is built in three versions:

**Insecure:** Plaintext JSON commands, no protection

**Secure:** PSK + AES-CBC + HMAC-SHA256 + Counter replay protection

**Vulnerable:** Secure looking, but uses a repeated IV to demonstrate potential implementation errors

## Security Protocol

Real drones lack the compute budget and battery capacity for asymmetric key exchange (e.g. Diffie-Hellman). This project uses a Pre-Shared Key (PSK) model, where both devices are provisioned with a shared secret before flight.

## Security Properties

| Mechanism | Threat Addressed | Security Property |
| --------- | ---------------- | ----------------- |
| AES-CBC | Eavesdropping / passive interception | Confidentiality |
| HMAC-SHA256 | Command forgery / tampering | Integrity + Authenticity |
| Counter | Replay attacks | Freshness
| Pre-shared Key | Compute / battery constraints on drone hardware | Practical deploy ability | 


## Setup

## Requirements
- Python 3.10 or higher
- External dependency: Cryptography

## Install Dependencies

In a terminal: git clone https://github.com/zgurley1/6200_Secure_Drone_Transmission

Run: python requirements.py

This will install cryptography if needed

**Manual Install**

Run: pip install cryptography

## Running Each Version

1. Insecure Version (Baseline)

  Commands are sent as plaintext JSON over the socket with no encryption, authentication, or replay protection. Any passive observer can read every command. Any attacker can modify or forge them.

  Open two terminals:

  Run: python drone.py

  Run: python controller.py

  Available commands:
  
  liftoff - take off, hover at z=10

  land - land the drone

  move <x> <y> <z> - move to coordinates (ex. move 1 5 12)

  status - print current drone state

  help - show command menu

  quit - disconnect

2. Secure Version (PSK + AES-CBC + HMAC + Counter)

   All commands are encrypted with AES-CBC, authenticated with HMAC-SHA256, and stamped with a counter. The controller displays the plaintext, counter, and encrypted envelope on each send so the security layer is visible

   Open two terminals:

    Run: python drone_secure.py
  
    Run: python controller_secure.py
  
    Available commands:
    
    liftoff - take off, hover at z=10
  
    land - land the drone
  
    move <x> <y> <z> - move to coordinates (ex. move 1 5 12)
  
    status - print current drone state
  
    help - show command menu
  
    quit - disconnect

 3. IV Reuse Version (Broken Implementation)

      While this version is functionally identical to the secure version, the implementation uses a hardcoded fixed IV instead of a random IV. For simplicity, this version does not use multiple files but instead
    simulates commands being sent.

    Run: python iv_analysis.py --simulate

## MITM Attack Demos

The attacker script (attacker.py) sits as a transparent proxy between the controller and drone. Every intercepted message is presented with three options:
  - [F] Forward - pass the message through untouched
  - [M] Modify - inject a forged command
  - [R] Replay - resend a previously captured message

** Demo A - Insecure**
