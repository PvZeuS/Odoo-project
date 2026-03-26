pipeline {
    agent any

    environment {
        EC2_USER     = 'ubuntu'
        EC2_IP       = branchIP()
        REMOTE_DIR   = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        ODOO_PORT            = branchPort()
        POSTGRES_DB          = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        POSTGRES_USER        = 'odoo'
        DB_PASS_SECRET       = credentials('odoo-db-password')
    }

    stages {
        stage('Disk Maintenance') {
            steps {
                echo "--- LIMPIEZA PREVENTIVA ---"
                // Borramos lo que falló anteriormente para empezar limpios
                sh 'docker system prune -f'
            }
        }

        stage('Linting') {
            steps {
                echo "--- INICIANDO LINTING DE CÓDIGO ---"
                sh '''
                    docker run --rm -v ${WORKSPACE}:/src -w /src python:3.10-slim sh -c "find . -path './addons*' -name '*.py' -exec python3 -m py_compile {} +"
                '''
            }
        }

        stage('Smart Unit Tests') {
            steps {
                script {
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def targetModule = getTargetModule(commitMsg)
                    
                    if (targetModule) {
                        echo "--- EJECUTANDO TESTS EN ODOO 19.0 ---"
                        sh """
                            docker network create test-net-${BUILD_NUMBER} || true
                            
                            docker run -d --name db-test-${BUILD_NUMBER} \
                                --network test-net-${BUILD_NUMBER} \
                                -e POSTGRES_PASSWORD='${DB_PASS_SECRET}' \
                                -e POSTGRES_USER=odoo \
                                postgres:15-alpine
                            
                            sleep 25
                            
                            # USAMOS ODOO 19.0 OFICIAL
                            docker run --rm --name odoo-test-${BUILD_NUMBER} \
                                --network test-net-${BUILD_NUMBER} \
                                -v \${WORKSPACE}/addons:/mnt/extra-addons \
                                odoo:19.0 odoo \
                                -d odoo_test --db_host db-test-${BUILD_NUMBER} \
                                --db_user odoo --db_password='${DB_PASS_SECRET}' \
                                -i base,${targetModule} --test-enable --stop-after-init --log-level=test
                        """
                    } else {
                        echo "--- SALTANDO TESTS: No se detectó 'MOD:modulo' ---"
                    }
                }
            }
            post {
                always {
                    sh """
                        docker stop db-test-${BUILD_NUMBER} || true
                        docker rm db-test-${BUILD_NUMBER} || true
                        docker network rm test-net-${BUILD_NUMBER} || true
                    """
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD='${DB_PASS_SECRET}'
                            
                            docker compose up -d --build --remove-orphans
                            sleep 15
                            docker compose run --rm odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init
                            docker compose restart odoo
EOF
                    '''
                }
            }
        }
    }

    post {
        success { echo "--- ¡TODO LISTO EN ODOO 19! http://${EC2_IP}:${ODOO_PORT} ---" }
        failure { echo "--- EL PIPELINE FALLÓ ---" }
        always {
            sh 'docker image prune -f'
        }
    }
}

@NonCPS
def getTargetModule(String msg) {
    def match = (msg =~ /MOD:([a-zA-Z0-9_]+)/)
    return match ? match[0][1] : null
}

def branchIP() { return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101' }
def branchPort() { return (env.BRANCH_NAME == 'main') ? '8071' : '8070' }