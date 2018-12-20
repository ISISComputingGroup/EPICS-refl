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
        setLatestGeniePath()
        echo "python path: ${env.PYTHON_PATH}"
        script {
            env.scmVars = checkout scm
            echo "git commit: ${env.scmVars.GIT_COMMIT}"
            echo "git branch: ${env.scmVars.BRANCH_NAME}"
        }
      }
    }
    
    stage("Run All Tests") {
      steps {
        bat """
            set PYTHON_PATH=${env.PYTHON_PATH}
            %PYTHON_PATH%\\Python\\python run_all_tests.py --output_dir ./test-reports
         """
      }
    }
        
    stage("Collate Unit Tests") {
      steps {
        junit '**/test-reports/TEST-*.xml'
        cobertura coberturaReportFile: '**/test-reports/coverage.xml'
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
            step([$class: 'CompareCoverageAction', scmVars: [env.scmVars]])
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
}

