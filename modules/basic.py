import sys


class BasicManager:
    def __init__(self, error_class):
        self.MarineError = error_class
        self.variables = {'아쎄이': 0}
        self._var_count = 0

    def parse_number(self, s: str, line_num: int) -> int:
        """해병 정수를 엄격하게 파싱한다!"""
        if not s:
            raise self.MarineError(f"[줄 {line_num}] 구문 오류: 숫자가 비어있다!")

        for char in s:
            if char not in ['악', '!', '아']:
                raise self.MarineError(f"[줄 {line_num}] 구문 오류: 정수 표기에 '악', '!', '아' 외의 흘러빠진 문자가 포함되어 있다!")

        is_negative = s.startswith('아')
        check_s = s[1:] if is_negative else s

        if '아' in check_s:
            raise self.MarineError(f"[줄 {line_num}] 구문 오류: '아'는 음수 표기를 위해 맨 앞에만 올 수 있다! 기열!")

        if not check_s.startswith('악'):
            raise self.MarineError(f"[줄 {line_num}] 구문 오류: 정수는 무조건 '악'으로 시작해야 한다!")

        parts = check_s.split('악')[1:]
        digits = []
        for p in parts:
            if len(p) >= 10:
                raise self.MarineError(f"[줄 {line_num}] 구문 오류: '악' 뒤에 '!'가 10개 이상 붙을 수 없다!")
            digits.append(str(len(p)))

        if not digits:
            return 0

        try:
            val = int("".join(digits))
            return -val if is_negative else val
        except ValueError:
            raise self.MarineError(f"[줄 {line_num}] 구문 오류: 올바르지 않은 해병 정수 형식이다!")

    def check_variable(self, var_name: str, line_num: int):
        """변수가 제대로 입대(선언)했는지 확인한다!"""
        if var_name not in self.variables:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: 선언되지 않은 변수를 사용했다! 미확인 인원 접근!")

    def get_value(self, token: str, line_num: int) -> int:
        """토큰이 변수면 값을 꺼내오고, 정수면 파싱해서 가져온다!"""
        if token.startswith('아쎄이'):
            self.check_variable(token, line_num)
            return self.variables[token]
        return self.parse_number(token, line_num)

    def declare(self, val_token: str, line_num: int):
        """신병 받아라: 새 변수를 선언하고 정수를 할당한다."""
        val = self.parse_number(val_token, line_num)
        self._var_count += 1
        var_name = '아쎄이' + ('!' * self._var_count)
        self.variables[var_name] = val

    def receive_input(self, line_num: int):
        """헤이빠빠리빠: stdin에서 정수를 읽어 아쎄이에 할당한다."""
        user_input = sys.stdin.readline().strip()
        try:
            self.variables['아쎄이'] = int(user_input)
        except ValueError:
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: '헤이빠빠리빠' 입력 시 해병 정수 외의 기열 값이 들어왔다!")

    def print_output(self, line_num: int):
        """라이라이 차차차: 아쎄이 값을 유니코드 문자로 출력한다."""
        val = self.variables.get('아쎄이', 0)
        try:
            print(chr(val), end='', flush=True)
        except (ValueError, OverflowError):
            raise self.MarineError(f"[줄 {line_num}] 런타임 오류: '아쎄이'에 유니코드로 변환 불가능한 수가 들어있다!")

    def add(self, var1: str, var2: str, line_num: int):
        """돌격: var1 += var2"""
        self.check_variable(var1, line_num)
        self.check_variable(var2, line_num)
        self.variables[var1] += self.variables[var2]

    def subtract(self, var1: str, var2: str, line_num: int):
        """역돌격: var1 -= var2"""
        self.check_variable(var1, line_num)
        self.check_variable(var2, line_num)
        self.variables[var1] -= self.variables[var2]
