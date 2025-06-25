import { describe, it, expect } from 'vitest';
import useStore from '../src/store';

describe('store', () => {
  it('updates factor', () => {
    useStore.getState().setFactor(2);
    expect(useStore.getState().factor).toBe(2);
  });
});
