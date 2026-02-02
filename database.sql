CREATE DATABASE nexovate26;
USE nexovate26;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id VARCHAR(20) UNIQUE,
    team_name VARCHAR(100),
    leader_email VARCHAR(100),
    payment_status ENUM('PENDING','WAITING','APPROVED') DEFAULT 'PENDING',
    transaction_id VARCHAR(50)
);

CREATE TABLE members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id VARCHAR(20),
    member_name VARCHAR(100),
    phone VARCHAR(15) UNIQUE,
    college_email VARCHAR(100) UNIQUE
);

CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(100)
);

-- Default Admin
INSERT INTO admin(username,password)
VALUES('csd','csda@2026');
