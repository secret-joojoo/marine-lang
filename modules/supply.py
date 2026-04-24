class SupplyManager:
    def __init__(self, error_class):
        # 순환 참조를 막기 위해 interpreter.py의 MarineError를 주입받아 사용해!
        self.MarineError = error_class
        self.is_ready = False
        self.warehouse_order = ['종합창고', '피복창고', '물류창고', '부식창고', '치장창고']
        self.warehouses = {w: None for w in self.warehouse_order}

    def prepare(self):
        """보급병! 과업 준비!"""
        self.is_ready = True

    def _check_ready(self, line_num):
        """보급병을 불렀는지 확인하는 기합찬 검사!"""
        if not self.is_ready:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 보급병을 부르지 않고 보급병 함수를 사용했다! 기열!")

    def move_to_warehouse(self, line_num):
        """보급병! 창고로 이동"""
        self._check_ready(line_num)
        for w in self.warehouse_order:
            if self.warehouses[w] is None:
                # 1번~256번 박스를 사용하므로 크기를 257로 할당해! (0번 인덱스는 더미)
                self.warehouses[w] = [None] * 257
                return
        raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 비어있는 창고가 없다! 무전취식인가!")

    def manage_warehouse(self, warehouse_name, idx_val, val, line_num):
        """보급병! (창고) 관리하겠습니다 (정수/변수1) (정수/변수2)"""
        self._check_ready(line_num)
        if warehouse_name not in self.warehouses or self.warehouses[warehouse_name] is None:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 선언되지 않은 창고({warehouse_name})를 관리하려고 했다! 기열!")
        
        if not (1 <= idx_val <= 256):
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 1번 ~ 256번 박스 외의 박스({idx_val})를 호출했다! 기열!")
            
        self.warehouses[warehouse_name][idx_val] = val

    def investigate_warehouse(self, warehouse_name, idx_val, line_num):
        """(변수) (창고) 조사하겠습니다 (정수/변수)"""
        self._check_ready(line_num)
        if warehouse_name not in self.warehouses or self.warehouses[warehouse_name] is None:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 선언되지 않은 창고({warehouse_name})를 조사하려고 했다! 기열!")
            
        if not (1 <= idx_val <= 256):
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 1번 ~ 256번 박스 외의 박스({idx_val})를 호출했다! 기열!")
            
        val = self.warehouses[warehouse_name][idx_val]
        if val is None:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 빈 박스를 호출했다! 기열!")
            
        return val

    def clear_warehouse(self, warehouse_name, line_num):
        """보급병! (창고) 정리하겠습니다"""
        self._check_ready(line_num)
        if warehouse_name not in self.warehouses or self.warehouses[warehouse_name] is None:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 사용 중인 창고가 없을 때({warehouse_name}) 정리하려고 했다! 기열!")
            
        self.warehouses[warehouse_name] = None