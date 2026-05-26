function Initialize-DevJobSupport {
    if ("DevJob.NativeMethods" -as [type]) {
        return
    }

    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace DevJob {
    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public UInt64 ReadOperationCount;
        public UInt64 WriteOperationCount;
        public UInt64 OtherOperationCount;
        public UInt64 ReadTransferCount;
        public UInt64 WriteTransferCount;
        public UInt64 OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public Int64 PerProcessUserTimeLimit;
        public Int64 PerJobUserTimeLimit;
        public UInt32 LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public UInt32 ActiveProcessLimit;
        public IntPtr Affinity;
        public UInt32 PriorityClass;
        public UInt32 SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    public static class NativeMethods {
        public const int JobObjectExtendedLimitInformation = 9;
        public const UInt32 JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

        [DllImport("kernel32.dll")]
        public static extern bool SetInformationJobObject(
            IntPtr hJob,
            int infoType,
            IntPtr lpJobObjectInfo,
            uint cbJobObjectInfoLength
        );

        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

        [DllImport("kernel32.dll")]
        public static extern bool CloseHandle(IntPtr hObject);
    }
}
"@
}

function Stop-ListeningPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        Write-Host "Stopping existing process on port $Port (pid $($listener.OwningProcess))"
        Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

function Start-ManagedDevProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$ArgumentList = @(),

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    Initialize-DevJobSupport

    $job = [DevJob.NativeMethods]::CreateJobObject([IntPtr]::Zero, $null)
    if ($job -eq [IntPtr]::Zero) {
        throw "Failed to create Windows job object."
    }

    $info = New-Object DevJob.JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    $info.BasicLimitInformation.LimitFlags = [DevJob.NativeMethods]::JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    $length = [Runtime.InteropServices.Marshal]::SizeOf([type][DevJob.JOBOBJECT_EXTENDED_LIMIT_INFORMATION])
    $infoPointer = [Runtime.InteropServices.Marshal]::AllocHGlobal($length)

    try {
        [Runtime.InteropServices.Marshal]::StructureToPtr($info, $infoPointer, $false)
        $configured = [DevJob.NativeMethods]::SetInformationJobObject(
            $job,
            [DevJob.NativeMethods]::JobObjectExtendedLimitInformation,
            $infoPointer,
            [uint32]$length
        )
        if (-not $configured) {
            throw "Failed to configure Windows job object."
        }

        $process = Start-Process `
            -FilePath $FilePath `
            -ArgumentList $ArgumentList `
            -WorkingDirectory $WorkingDirectory `
            -NoNewWindow `
            -PassThru

        $assigned = [DevJob.NativeMethods]::AssignProcessToJobObject($job, $process.Handle)
        if (-not $assigned) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            throw "Failed to assign process $($process.Id) to Windows job object."
        }

        Write-Host "Started managed process pid $($process.Id). Closing this terminal will stop it."
        Wait-Process -Id $process.Id
    }
    finally {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
        [DevJob.NativeMethods]::CloseHandle($job) | Out-Null
        [Runtime.InteropServices.Marshal]::FreeHGlobal($infoPointer)
    }
}
