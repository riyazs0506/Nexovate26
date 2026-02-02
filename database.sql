-- ===============================
-- DATABASE
-- ===============================
CREATE DATABASE IF NOT EXISTS nexovate26;
USE nexovate26;

-- ===============================
-- USERS TABLE
-- ===============================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===============================
-- TEAMS TABLE
-- ===============================
CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id VARCHAR(20) UNIQUE NOT NULL,          -- NXABC123
    team_name VARCHAR(100),                       -- NULL for workshop-only
    leader_email VARCHAR(100) NOT NULL,

    registration_type ENUM(
        'workshop',
        'workshop_technical',
        'technical_nontechnical'
    ) NOT NULL DEFAULT 'workshop',

    payment_status ENUM(
        'PENDING',
        'WAITING',
        'APPROVED'
    ) DEFAULT 'PENDING',

    transaction_id VARCHAR(50),

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
    student_id VARCHAR(25) UNIQUE NOT NULL,   -- NXABC123-01

    member_name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    college_email VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON DELETE CASCADE
);

-- ===============================
-- ADMIN TABLE
-- ===============================
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);



ALTER TABLE teams
ADD COLUMN amount_paid INT DEFAULT 0;
