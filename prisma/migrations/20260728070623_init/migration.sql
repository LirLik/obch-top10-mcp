-- CreateTable
CREATE TABLE `scores` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `external_id` INTEGER NULL,
    `rank` INTEGER NOT NULL,
    `player_name` VARCHAR(64) NOT NULL,
    `score` INTEGER NOT NULL,
    `lines_cleared` INTEGER NOT NULL DEFAULT 0,
    `level` INTEGER NOT NULL DEFAULT 1,
    `duration_seconds` INTEGER NOT NULL DEFAULT 0,
    `played_at` DATETIME(3) NULL,
    `source` VARCHAR(255) NOT NULL,
    `synced_at` DATETIME(3) NOT NULL,

    INDEX `scores_rank_idx`(`rank`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `sync_events` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `source` VARCHAR(255) NOT NULL,
    `scores_count` INTEGER NOT NULL,
    `payload_json` JSON NOT NULL,
    `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX `sync_events_created_at_idx`(`created_at`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
