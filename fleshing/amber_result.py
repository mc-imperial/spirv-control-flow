# Copyright 2022 The SPIRV-Control Flow Project Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class AmberResult:

    def __init__(self, filename, return_code=-1, stdout="", stderr="", is_timed_out=False):
        self.filename = filename
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.is_timed_out = is_timed_out
    
    def __str__(self):
        success_str = "Success" if self.return_code == 0 else "Failure"
        ret = f"{success_str}: {self.filename}"
        if self.is_timed_out:
            ret += "\nAMBER TIMED OUT\n"
        ret += self.stdout
        ret += self.stderr
        return ret
