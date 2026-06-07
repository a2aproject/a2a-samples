CREATE TABLE IF NOT EXISTS `tasks` (
    `task_id`    CHAR(36) PRIMARY KEY,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `user`       VARCHAR(255) NOT NULL DEFAULT '',
    `agent`      VARCHAR(255) NOT NULL DEFAULT '',
    `context_id` VARCHAR(255) NOT NULL DEFAULT '',
    `state`      VARCHAR(32) NOT NULL DEFAULT 'submitted',
    `version`    BIGINT NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE INDEX `idx_tasks_state_created` ON `tasks` (`state`, `updated_at`);
CREATE INDEX `idx_tasks_context_created` ON `tasks` (`context_id`, `created_at`);
CREATE INDEX `idx_tasks_user_created` ON `tasks` (`user`, `created_at`);
CREATE INDEX `idx_tasks_agent_created` ON `tasks` (`agent`, `created_at`);

CREATE TABLE IF NOT EXISTS `outbox` (
    `id`         BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `task_id`    CHAR(36) NOT NULL,
    `agent`      VARCHAR(255) NOT NULL,
    `event_data` TEXT NOT NULL
) ENGINE=InnoDB;

CREATE INDEX `idx_outbox_agent` ON `outbox` (`agent`, `id`);