# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for HistoryManager (Undo / Redo state stack)."""

import numpy as np
import pytest

from ai_texture_painter.texture.history import HistoryManager, get_history_manager


class TestHistoryManager:
    def setup_method(self):
        """Her testten önce geçmişi sıfırla."""
        get_history_manager().clear()

    def teardown_method(self):
        get_history_manager().clear()

    def test_push_and_undo_redo(self):
        """Temel push, undo ve redo akış testi."""
        mgr = get_history_manager()

        img0 = np.zeros((16, 16, 4), dtype=np.float32)
        img1 = np.ones((16, 16, 4), dtype=np.float32) * 0.5
        img2 = np.ones((16, 16, 4), dtype=np.float32)

        mgr.push("Step 0", img0)
        assert not mgr.can_undo
        assert not mgr.can_redo

        mgr.push("Step 1", img1)
        assert mgr.can_undo
        assert not mgr.can_redo

        mgr.push("Step 2", img2)
        assert mgr.can_undo

        # Undo -> Step 1
        entry = mgr.undo()
        assert entry is not None
        assert entry.label == "Step 1"
        np.testing.assert_allclose(entry.pixels, img1)
        assert mgr.can_undo
        assert mgr.can_redo

        # Undo -> Step 0
        entry0 = mgr.undo()
        assert entry0 is not None
        assert entry0.label == "Step 0"
        assert not mgr.can_undo
        assert mgr.can_redo

        # Redo -> Step 1
        entry_re = mgr.redo()
        assert entry_re is not None
        assert entry_re.label == "Step 1"

    def test_branching_truncates_redo(self):
        """Undo sonrası yeni push yapıldığında ileri (redo) geçmişinin silinmesi testi."""
        mgr = get_history_manager()
        imgA = np.zeros((8, 8, 4), dtype=np.float32)
        imgB = np.ones((8, 8, 4), dtype=np.float32)
        imgC = np.full((8, 8, 4), 0.75, dtype=np.float32)

        mgr.push("A", imgA)
        mgr.push("B", imgB)
        mgr.undo()  # Now at A, can_redo is True (pointing to B)
        assert mgr.can_redo

        mgr.push("C", imgC)  # Branching
        assert not mgr.can_redo
        assert mgr.can_undo
        assert mgr.current_entry.label == "C"

    def test_bounded_history_capacity(self):
        """Maksimum sınır aşıldığında en eski elemanın çıkarılması testi."""
        mgr = get_history_manager()
        max_cap = mgr.MAX_HISTORY

        for i in range(max_cap + 5):
            img = np.full((4, 4, 4), i, dtype=np.float32)
            mgr.push(f"Step {i}", img)

        assert len(mgr._stack) == max_cap
        # En eski eleman Step 5 olmalı
        assert mgr._stack[0].label == "Step 5"
        assert mgr.current_entry.label == f"Step {max_cap + 4}"
