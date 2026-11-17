"""MSB-first shortened BCH(592,512), m=10,t=8, polynomial x^10+x^3+1."""
import bchlib
import numpy as np

class BCH512:
    def __init__(self):
        self.code = bchlib.BCH(8, m=10)
        assert self.code.ecc_bits == 80 and self.code.prim_poly == 0x409

    def encode(self, bits):
        bits = np.asarray(bits, dtype=np.uint8)
        if bits.shape != (512,) or not np.isin(bits, [0, 1]).all():
            raise ValueError("Expected 512 binary information bits")
        data = np.packbits(bits, bitorder="big").tobytes()
        # Leading shortened zeros do not change the encoder remainder. libbch's
        # shortened-byte interface implicitly restores that prefix for decoding.
        return np.unpackbits(np.frombuffer(data + self.code.encode(data), dtype=np.uint8), bitorder="big")

    def decode(self, soft):
        soft = np.asarray(soft)
        if soft.shape != (592,) or not np.isfinite(soft).all():
            raise ValueError("Expected 592 finite signed responses")
        hard = (soft > 0).astype(np.uint8)
        packed = np.packbits(hard, bitorder="big").tobytes()
        data, ecc = bytearray(packed[:64]), bytearray(packed[64:])
        count = self.code.decode(data, ecc)
        if count >= 0:
            self.code.correct(data, ecc)
            # Re-encoding verifies the syndrome, including all 80 parity bits.
            if self.code.encode(data) == bytes(ecc):
                return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="big"), {"bch_success": True, "corrected_bits": count}
        return hard[:512], {"bch_success": False, "corrected_bits": None}
