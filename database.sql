-- ===============================
-- DATABASE
-- ===============================
CREATE DATABASE IF NOT EXISTS nexovate26;
USE nexovate26;

-- ===============================
-- TEAMS TABLE
-- ===============================
CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id VARCHAR(20) UNIQUE NOT NULL,
    team_name VARCHAR(100),

    leader_name VARCHAR(100) NOT NULL,
    leader_email VARCHAR(100) NOT NULL,

    registration_type ENUM(
        'technical',
        'technical_nontech',
        'technical_nontech_workshop'
    ) NOT NULL,

    member_count INT NOT NULL,

    amount_paid INT DEFAULT 0,

    payment_status ENUM(
        'PENDING',
        'WAITING',
        'APPROVED'
    ) DEFAULT 'PENDING',

    transaction_id VARCHAR(50),
    status_token VARCHAR(100) UNIQUE NOT NULL,

    certificate_enabled TINYINT DEFAULT 0,
    event_completed TINYINT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX (team_id),
    INDEX (leader_email)
);

-- ===============================
-- MEMBERS TABLE
-- ===============================
CREATE TABLE members (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id VARCHAR(20) NOT NULL,
    student_id VARCHAR(30) UNIQUE NOT NULL,

    member_name VARCHAR(100) NOT NULL,
    study_year ENUM('I','II','III','IV') NOT NULL,
    department VARCHAR(100) NOT NULL,
    college_name VARCHAR(150) NOT NULL,

    phone VARCHAR(15) UNIQUE NOT NULL,
    college_email VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON DELETE CASCADE
);

-- ===============================
-- EVENTS MASTER TABLE
-- ===============================
CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,

    event_name VARCHAR(100) UNIQUE NOT NULL,
    category ENUM('technical','non_technical','workshop') NOT NULL,

    max_participants INT DEFAULT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===============================
-- SEED EVENTS (FINAL & CONSISTENT)
-- ===============================
INSERT INTO events (event_name, category, max_participants) VALUES
('CodeXtreme', 'technical', NULL),
('Paper Presentation', 'technical', NULL),
('UI Challenge', 'technical', NULL),

('Clueminati', 'non_technical', NULL),
('Deck Clash', 'non_technical', NULL),
('Story Spade', 'non_technical', NULL),
('IPL Auction', 'non_technical', NULL),

('Figma', 'workshop', 30),
('ARVR', 'workshop', 30);

-- ===============================
-- TEAM EVENTS
-- ===============================
CREATE TABLE team_events (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id VARCHAR(20) NOT NULL,
    event_name VARCHAR(100) NOT NULL,

    event_category ENUM('technical','non_technical') NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON DELETE CASCADE,

    FOREIGN KEY (event_name)
        REFERENCES events(event_name)
        ON DELETE CASCADE
);

-- ===============================
-- WORKSHOP REGISTRATIONS
-- ===============================
CREATE TABLE workshop_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,

    member_id INT NOT NULL,
    workshop_name VARCHAR(100) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (member_id)
        REFERENCES members(id)
        ON DELETE CASCADE,

    FOREIGN KEY (workshop_name)
        REFERENCES events(event_name)
        ON DELETE CASCADE,

    UNIQUE (member_id)
);

-- ===============================
-- WORKSHOP COUNT VIEW
-- ===============================
CREATE VIEW workshop_count AS
SELECT
    workshop_name,
    COUNT(*) AS total_registered
FROM workshop_registrations
GROUP BY workshop_name;

-- ===============================
-- ADMIN TABLE
-- ===============================
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);

