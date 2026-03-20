# AI-Powered Parametric Insurance for Gig Workers

---

##  1. Problem Overview

Gig economy delivery workers (Zomato, Swiggy, etc.) rely on **daily earnings**.
However, external disruptions such as **heavy rain, pollution, curfews, and zone closures** can reduce their working hours, causing **significant income loss (20–30%)**.

Currently, there is **no protection mechanism** for such uncontrollable disruptions.

---

##  2. Target Persona & Scenarios

### Persona: Food Delivery Rider (Zomato/Swiggy)

* Works during **peak hours (lunch & dinner)**
* Earns ₹800–₹1200 daily
* Highly dependent on weather and local conditions

---

### Scenario 1: Heavy Rain (Peak Hours)

* Time: 7–10 PM
* Condition: Heavy rainfall
* Impact: Orders drop / deliveries halted
* Loss: ₹150–₹300

---

### Scenario 2: High Pollution (AQI > 400)

* Rider avoids working due to unsafe conditions
* Reduced working hours
* Loss: ₹100–₹200

---

### Scenario 3: Curfew 

* Area becomes inaccessible
* No deliveries possible
* Loss: ₹650–₹1000

---

### Scenario 4: Zone Closure

* Forced to reallocate
* Deliveries in unfamiliar places
* Loss: ₹300–₹500

---

## ⚙️ 3. System Workflow

1. **User Onboarding**

   * Worker registers and provides location + work pattern

2. **Risk Profiling (AI)**

   * System calculates risk score based on:

     * Location
     * Weather trends
     * Historical disruptions

3. **Weekly Policy Purchase**

   * Worker selects coverage plan
   * Dynamic premium is generated

4. **Real-Time Monitoring**

   * System continuously monitors:

     * Weather APIs
     * AQI levels
     * Event data (strikes/closures)

5. **Trigger Detection**

   * If disruption crosses threshold → event triggered

6. **Validation Layer**

   * Check:

     * Worker activity
     * Location authenticity
     * Income impact

7. **Automatic Payout**

   * Claim auto-processed
   * Instant payout simulated

---

## ⚡ 4. Parametric Trigger Design

Our system uses **data-driven triggers**, not manual claims.

### Example Triggers:

* Rainfall > 50 mm in 2 hours
* AQI > 300 (Hazardous)
* Curfew / strike detected via event API

---

###  Trigger Logic

> **Payout = Event + Active Worker + Verified Impact**

* Event occurs
* Worker is actively delivering
* Income loss is validated

---

## 5. Weekly Dynamic Premium Model

Premium is calculated **weekly** based on risk.

### 🔹 Formula

```
Premium = Base Price × Risk Multiplier × Coverage Factor
```

---

### 🔹 Factors Considered

* Location risk (flood-prone, high AQI zones)
* Weather forecast (upcoming week)
* Worker activity pattern
* Expected earnings

---

### 🔹 Example

* Low risk worker → ₹15/week
* High risk worker → ₹30/week

---

## 🤖 6. AI/ML Integration

### 🔹 Risk Prediction

* Predict probability of disruptions
* Generate risk score for each worker

---

### 🔹 Dynamic Pricing

* Adjust weekly premium based on:

  * Forecast + historical data

---

### 🔹 Fraud Detection

* Detect:

  * GPS spoofing
  * Duplicate claims
  * Abnormal patterns

---

## 🔐 7. Fraud Prevention Strategy

We implement **multi-layer validation**:

* Multi-signal location verification (GPS + network)
* Activity validation (delivery logs)
* Movement pattern analysis
* Minimum time in disruption zone
* Earnings impact validation
* Event-based deduplication

> **Key Principle:**
> “We validate impact, not just location.”

---

## 8. Data Sources & APIs

### Used APIs:

* Weather → OpenWeatherMap
* Pollution → CPCB AQI
* Events → GDELT
* Zone closures → OSM / simulated

---

## 9. Tech Stack

### Frontend

* Mobile-first (Flutter / React Native)

### Backend

* Node.js / Python (FastAPI)

### AI/ML

* Python (scikit-learn / basic models)

### Database

* MongoDB / PostgreSQL

### APIs

* Weather, AQI, Event APIs

### Payments

* Razorpay (test mode)

---

##  10. Platform Choice (Mobile First)

We choose a **Mobile Application** because:

* Delivery workers primarily use smartphones
* Real-time notifications are critical
* Better integration with GPS and activity tracking

---

##  11. Development Plan

### Phase 1

* Ideation, workflow design, architecture

### Phase 2

* Core features:

  * Onboarding
  * Premium calculation
  * Trigger system

### Phase 3

* Advanced features:

  * Fraud detection
  * Dashboard
  * Optimization

---

## 12. Key Innovations

* Multi-factor parametric triggers
* AI-driven personalized pricing
* Earnings-based payout logic
* Zero-touch claim system
* Fraud-resistant architecture

---

## Demo & Repository

* 📹 Demo Video: [Insert Link]

---

# 🧠 Final Statement

> Our solution transforms insurance from a reactive, manual process into a **proactive, automated safety net** that protects gig workers’ income in real time.


