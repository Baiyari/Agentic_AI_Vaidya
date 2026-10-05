CREATE TABLE IF NOT EXISTS vaidya_cases (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  patient_id TEXT NOT NULL,
  chief_complaint TEXT,
  symptoms JSONB,
  age INT,
  duration_days INT,
  severity TEXT,
  score INT,
  reason TEXT,
  specialty TEXT,
  impression TEXT,
  differentials JSONB,
  actions JSONB,
  citations JSONB,
  trace JSONB,
  report TEXT
);
CREATE INDEX IF NOT EXISTS idx_vaidya_cases_patient ON vaidya_cases (patient_id, created_at DESC);
