#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label "windows"
  }
  
  triggers {
    pollSCM('H/2 * * * *')
  }
  
  stages {  
    stage("Checkout") {
      steps {
        echo "Branch: ${env.BRANCH_NAME}"
        checkout scm
        setLatestGeniePath()
        echo "python path: ${env.PYTHON_PATH}"
        script {
            env.GIT_COMMIT = bat(returnStdout: true, script: '@git rev-parse HEAD').trim()
            echo "git commit: ${env.GIT_COMMIT}"
            echo "git branch: ${env.BRANCH_NAME}"
            echo "git change id: ${env.CHANGE_ID}"
            echo "git change url: ${env.CHANGE_URL}"
        }
      }
    }
    
    stage("Run All Tests") {
      steps {
        bat """
            robocopy "\\\\isis\\inst\$\\Kits\$\\CompGroup\\ICP\\EPICS_UTILS" "C:\\Instrument\\Apps\\EPICS_UTILS" /E /PURGE /R:2 /MT /XF "install.log" /NFL /NDL /NP
            set "PATH=%PATH%;C:\\Instrument\\Apps\\EPICS_UTILS"
            
            set PYTHON_PATH=${env.PYTHON_PATH}
            %PYTHON_PATH%\\Python\\python run_all_tests.py --output_dir ./test-reports
            
            set PYTHON3_PATH=${env.PYTHON3_PATH}
            %PYTHON3_PATH%\\Python\\python run_all_tests.py --output_dir ./test-reports
         """
      }
    }
        
    stage("Collate Unit Tests") {
      steps {
        junit '**/test-reports/TEST-*.xml'
        script {
          if (fileExists('**/cobertura.xml')) {
            cobertura coberturaReportFile: '**/cobertura.xml'
          }
        }
      }
    }

    stage("Record Coverage") {
        when { branch 'master' }
        steps {            
            script {
                currentBuild.result = 'SUCCESS'
            }
            step([$class: 'MasterCoverageAction', scmVars: [GIT_URL: env.GIT_URL]])
        }
    }

    stage("PR Coverage to Github") {
        when { not { branch 'master' }}
        steps {
            script {
                currentBuild.result = 'SUCCESS'
            }
            step([$class: 'CompareCoverageAction', scmVars: [GIT_URL: env.GIT_URL]])
        }
    }
    
  }
  
  post {
    failure {
      step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: 'icp-buildserver@lists.isis.rl.ac.uk', sendToIndividuals: true])
    }
  }
  
  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'10'))
    timeout(time: 60, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
}

def setLatestGeniePath() {
    def basePath = '\\\\isis\\inst$\\Kits\$\\CompGroup\\ICP\\genie_python\\'
    def fileContents = readFile basePath + 'LATEST_BUILD.txt'
    def pythonPath = basePath + "BUILD-$fileContents"
    env.PYTHON_PATH = pythonPath
    
    def basePath3 = '\\\\isis\\inst$\\Kits\$\\CompGroup\\ICP\\genie_python\\'
    def fileContents3 = readFile basePath + 'LATEST_BUILD.txt'
    def pythonPath3 = basePath + "BUILD-$fileContents"
    env.PYTHON3_PATH = pythonPath
}

