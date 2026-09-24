-- =====================================================================
-- WeatherWatch Database Schema for Supabase (PostgreSQL)
-- Run this script in: Supabase Dashboard -> SQL Editor -> New Query -> Run
-- =====================================================================

-- Drop table if you need a clean reset (optional, commented out)
-- DROP TABLE IF EXISTS reports CASCADE;

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,

    -- Submitter identity
    submitter_name VARCHAR(120) NOT NULL,
    submitter_email VARCHAR(200),
    source_type VARCHAR(40) DEFAULT 'citizen',        -- citizen | social_media | official
    account_age_months INTEGER DEFAULT 0,
    is_verified_account BOOLEAN DEFAULT FALSE,
    prior_verified_count INTEGER DEFAULT 0,

    -- Event details
    event_category VARCHAR(80) NOT NULL,              -- flood | cyclone | heatwave | rain | fog | hailstorm | drought | thunderstorm
    description TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'moderate',          -- low | moderate | high | extreme

    -- Location
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),

    -- Media
    image_url VARCHAR(500),
    image_exif_valid BOOLEAN,

    -- Status & review
    status VARCHAR(20) DEFAULT 'pending',             -- pending | published | flagged | rejected | merged
    merged_into_id INTEGER,
    admin_note TEXT,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,

    -- ML outputs & Credibility Scoring (0 to 100)
    classified_category VARCHAR(80),
    classification_confidence DOUBLE PRECISION,
    credibility_score DOUBLE PRECISION,
    score_breakdown JSONB,                             -- Step 1, Step 2, Step 3 breakdown
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id INTEGER,

    -- Geo-verification (IMD station cross-referencing)
    nearest_imd_station VARCHAR(200),
    imd_distance_km DOUBLE PRECISION,
    imd_match BOOLEAN,
    geo_score_detail TEXT,

    -- Timestamps
    event_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Consent
    consent_given BOOLEAN DEFAULT FALSE
);

-- Indexes for lightning-fast queries and geospatial filtering
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_category ON reports(event_category);
CREATE INDEX IF NOT EXISTS idx_reports_credibility ON reports(credibility_score);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_lat_lon ON reports(latitude, longitude);

-- Sample initial test data (Optional — to immediately verify on your map)
INSERT INTO reports (
    submitter_name, submitter_email, source_type, event_category, description,
    severity, latitude, longitude, city, state, status, credibility_score,
    nearest_imd_station, imd_distance_km, imd_match, consent_given
) VALUES 
(
    'Ramesh Kumar', 'ramesh@example.com', 'citizen', 'flood',
    'Severe waterlogging up to waist level on Velachery main road. Vehicles stranded.',
    'high', 12.9759, 80.2212, 'Chennai', 'Tamil Nadu', 'published', 88.5,
    'Meenambakkam IMD Station', 4.2, TRUE, TRUE
),
(
    'Anita Roy', 'anita@example.com', 'citizen', 'rain',
    'Continuous heavy downpour for past 3 hours near Salt Lake sector 5.',
    'moderate', 22.5867, 88.4178, 'Kolkata', 'West Bengal', 'published', 79.0,
    'Dum Dum Airport IMD', 6.8, TRUE, TRUE
),
(
    'Vikram Singh', 'vikram@example.com', 'citizen', 'cyclone',
    'Gale force winds blowing away tin roofs and tree branches near RK beach.',
    'extreme', 17.7126, 83.3235, 'Visakhapatnam', 'Andhra Pradesh', 'published', 92.0,
    'Visakhapatnam Cyclone Warning Centre', 3.1, TRUE, TRUE
);
