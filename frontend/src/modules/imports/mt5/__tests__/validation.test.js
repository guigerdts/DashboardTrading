import { describe, it, expect } from 'vitest';
import { validateFile } from '../hooks/useImportFlow';

describe('validateFile', () => {
  it('allows .csv files', () => {
    const file = new File(['content'], 'test.csv', { type: 'text/csv' });
    expect(validateFile(file)).toBeNull();
  });

  it('allows .CSV files (case-insensitive)', () => {
    const file = new File(['content'], 'DATA.CSV', { type: 'text/csv' });
    expect(validateFile(file)).toBeNull();
  });

  it('allows mixed-case .Csv files', () => {
    const file = new File(['content'], 'data.Csv', { type: 'text/csv' });
    expect(validateFile(file)).toBeNull();
  });

  it('rejects .xlsx files with appropriate error', () => {
    const file = new File(['content'], 'data.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    expect(validateFile(file)).toBe('File must be a .csv');
  });

  it('rejects files larger than 5MB', () => {
    // size = 5MB + 1 byte
    const file = new File(['x'.repeat(5 * 1024 * 1024 + 1)], 'large.csv', { type: 'text/csv' });
    expect(validateFile(file)).toBe('File must be ≤ 5 MB');
  });

  it('allows files exactly 5MB', () => {
    // boundary test: exactly 5MB is valid per design
    const file = new File(['x'.repeat(5 * 1024 * 1024)], 'exact.csv', { type: 'text/csv' });
    expect(validateFile(file)).toBeNull();
  });

  it('allows files smaller than 5MB', () => {
    const file = new File(['small content'], 'small.csv', { type: 'text/csv' });
    expect(validateFile(file)).toBeNull();
  });

  it('rejects null file with appropriate error', () => {
    expect(validateFile(null)).toBe('Please select a file');
  });
});
