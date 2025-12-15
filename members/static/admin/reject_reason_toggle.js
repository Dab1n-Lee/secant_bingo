// 반려 사유 입력 필드는 반려 액션/상태에서만 노출되도록 토글한다.
(function() {
    document.addEventListener("DOMContentLoaded", function() {
        // Change form에서 status 선택 시 토글
        const statusSelect = document.getElementById("id_status");
        const reasonRow = document.querySelector(".field-rejected_reason");
        const toggleStatus = () => {
            if (!statusSelect || !reasonRow) return;
            reasonRow.style.display = statusSelect.value === "rejected" ? "" : "none";
        };
        toggleStatus();
        if (statusSelect) statusSelect.addEventListener("change", toggleStatus);

        // 리스트 액션에서 반려 액션 선택 시 토글
        const actionSelect = document.querySelector('select[name="action"]');
        const actionReasonRow = document.querySelector(".field-rejection_reason");
        const toggleAction = () => {
            if (!actionSelect || !actionReasonRow) return;
            actionReasonRow.style.display = actionSelect.value === "reject_selected" ? "" : "none";
        };
        toggleAction();
        if (actionSelect) actionSelect.addEventListener("change", toggleAction);
    });
})();
