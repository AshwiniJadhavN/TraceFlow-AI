/**
 * TraceFlow AI Orchestrator Load Testing
 * 
 * Tests orchestrator performance under load:
 * - Sustained throughput: 10 concurrent users
 * - Ramp-up: 30 seconds to full load
 * - Duration: 5 minutes
 * - Target latency: <60 seconds per requirement
 * 
 * Run: k6 run tests/load/k6-orchestrator-load.js
 * Report: HTML summary generated to htmlreport/
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

// ============================================================================
// Custom Metrics
// ============================================================================

const orchestrationTime = new Trend('orchestration_time');
const failureRate = new Rate('failures');
const throughputCounter = new Counter('requests_completed');
const activeVUs = new Gauge('active_vus');

// ============================================================================
// Test Configuration
// ============================================================================

export const options = {
  // Scenario: Sustained load with gradual ramp-up
  stages: [
    { duration: '30s', target: 5 },   // Ramp-up to 5 users
    { duration: '2m', target: 10 },   // Ramp-up to 10 users
    { duration: '3m', target: 10 },   // Sustain 10 users
    { duration: '1m', target: 0 },    // Cool down
  ],

  // Fail if error rate exceeds 5%
  thresholds: {
    'failures': ['rate<0.05'],
    'orchestration_time': ['p(95)<60000'],  // 95th percentile < 60 seconds
  },

  // Extended timeout for processing requirements
  httpDebug: 'full',
};

// ============================================================================
// Test Data
// ============================================================================

const testRequirements = [
  {
    device_name: "Cardiac Monitor V1",
    requirement: "Monitor patient heart rate and alert on abnormalities",
    regulatory_context: "FDA Class II, IEC 62304 Class C",
    intended_use: "Continuous patient monitoring in hospital setting",
  },
  {
    device_name: "Glucose Meter",
    requirement: "Accurately measure blood glucose levels within ±10%",
    regulatory_context: "FDA Class II, IEC 62304 Class B",
    intended_use: "Point-of-care glucose measurement",
  },
  {
    device_name: "Drug Infusion Pump",
    requirement: "Deliver medications at precise rates with safety interlocks",
    regulatory_context: "FDA Class III, IEC 62304 Class C",
    intended_use: "Inpatient medication administration",
  },
];

// ============================================================================
// Setup Phase
// ============================================================================

export function setup() {
  console.log('TraceFlow Load Test: Starting');
  return { startTime: new Date() };
}

// ============================================================================
// Main Test Function
// ============================================================================

export default function (data) {
  activeVUs.value = __VU;

  group('TraceFlow Orchestration', () => {
    // Select random requirement
    const requirement = testRequirements[Math.floor(Math.random() * testRequirements.length)];

    // Prepare payload
    const payload = JSON.stringify({
      requirement: requirement.requirement,
      device_name: requirement.device_name,
      regulatory_context: requirement.regulatory_context,
      intended_use: requirement.intended_use,
    });

    // Execute orchestration
    const startTime = new Date();
    const response = http.post(
      `http://localhost:8000/analyze`,
      payload,
      {
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'k6-load-test',
        },
        timeout: '120s',
      }
    );
    const endTime = new Date();
    const duration = endTime - startTime;

    // Record metrics
    orchestrationTime.add(duration);
    throughputCounter.add(1);
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 60s': (r) => duration < 60000,
      'response has analysis': (r) => r.json('analysis') !== undefined,
      'response has hazards': (r) => r.json('analysis.identified_hazards') !== undefined,
      'response has security': (r) => r.json('analysis.security_assessment') !== undefined,
    });

    if (!success) {
      console.error(`Failed request: ${response.status} (${duration}ms)`);
      failureRate.add(!success);
    }

    // Simulate realistic think time
    sleep(Math.random() * 3 + 2);
  });

  group('Analysis Retrieval', () => {
    // Simulate retrieving previous analysis results
    const analysisId = `analysis_${Math.floor(Math.random() * 1000)}`;

    const response = http.get(
      `http://localhost:8000/analysis/${analysisId}`,
      {
        headers: {
          'User-Agent': 'k6-load-test',
        },
      }
    );

    check(response, {
      'status is 200 or 404': (r) => r.status === 200 || r.status === 404,
    });

    sleep(1);
  });
}

// ============================================================================
// Teardown Phase
// ============================================================================

export function teardown(data) {
  console.log('TraceFlow Load Test: Complete');
  console.log(`Started: ${data.startTime}`);
  console.log(`Ended: ${new Date()}`);
}

/**
 * Expected Results (10 users, 6 minutes):
 * 
 * Throughput: ~60 requests (10 users * 6 min, avg 1 req/min per user)
 * Success Rate: >95%
 * P95 Latency: <60 seconds (regulatory requirement)
 * P99 Latency: <90 seconds (design margin)
 * 
 * Performance Targets:
 * - Classification: <5 seconds
 * - Hazard Analysis: <15 seconds
 * - FMEA/FTA/Security: <30 seconds (parallel)
 * - Consolidation: <5 seconds
 * - Total: <55 seconds (5 sec buffer)
 * 
 * If latency exceeds targets:
 * 1. Profile with: make profile
 * 2. Check LLM API latency
 * 3. Review agent parallelism
 * 4. Consider caching repeated requirements
 */
