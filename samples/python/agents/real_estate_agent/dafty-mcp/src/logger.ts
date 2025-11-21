import winston from 'winston';
import path from 'node:path';

const logsDir = path.join(process.cwd(), 'logs');
const logFileName = `daft_mcp.log`;
const logFilePath = path.join(logsDir, logFileName);

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.splat(),
    winston.format.printf((info) => {
      const { timestamp, level, message } = info;
      const splat = info[Symbol.for('splat')] as unknown[];
      const splatStr = splat ? splat.map((s: unknown) => JSON.stringify(s, null, 2)).join('\n') : '';
      return `${timestamp} ${level}: ${message}${splatStr ? '\n' + splatStr : ''}`;
    })
  ),
  transports: [new winston.transports.File({ filename: logFilePath })],
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(
    new winston.transports.Console({
      format: winston.format.simple(),
    })
  );
}

export default logger;
