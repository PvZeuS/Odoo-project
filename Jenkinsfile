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
        POSTGRES_PASSWORD    = credentials('odoo-db-password')
    }

    stages {
        stage('Linting') {
            steps {
                echo "Analizando sintaxis de los módulos..."
                // Analiza todo el código de addons rápidamente
                sh 'docker run --rm -v $(pwd):/mnt vauxoo/odoo-linter:latest pylint --rcfile=/mnt/.pylintrc /mnt/addons'
            }
        }

        stage('Smart Unit Tests') {
            steps {
                script {
                    // 1. Intentar obtener el módulo desde el mensaje del commit (Ej: "MOD:modulo_prueba")
                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    def match = (commitMsg =~ /MOD:([a-zA-Z0-9_]+)/)
                    def changedModules = ""

                    if (match) {
                        changedModules = match[0][1]
                        echo "Módulo forzado por commit: ${changedModules}"
                    } else {
                        // 2. Si no hay palabra clave, detectar por archivos cambiados
                        changedModules = sh(
                            script: "git diff --name-only HEAD~1 HEAD | grep '^addons/' | cut -d/ -f2 | sort -u | paste -sd ',' -",
                            returnStdout: true
                        ).trim()
                        echo "Módulos detectados por cambios en archivos: ${changedModules}"
                    }

                    if (changedModules) {
                        sh """
                            docker network create test-net-${BUILD_NUMBER}
                            docker run -d --name db-test-${BUILD_NUMBER} --network test-net-${BUILD_NUMBER} -e POSTGRES_PASSWORD=odoo -e POSTGRES_USER=odoo postgres:15-alpine
                            sleep 10
                            
                            docker run --rm --name odoo-test-${BUILD_NUMBER} \
                                --network test-net-${BUILD_NUMBER} \
                                -v \$(pwd)/addons:/mnt/extra-addons \
                                odoo:19.0 odoo \
                                -d odoo_test --db_host db-test-${BUILD_NUMBER} --db_user odoo --db_password odoo \
                                -i base,${changedModules} --test-enable --stop-after-init --log-level=test
                        """
                    } else {
                        echo "No se detectaron módulos para testear. Saltando etapa."
                    }
                }
            }
            post {
                always {
                    sh "docker stop db-test-${BUILD_NUMBER} || true; docker rm db-test-${BUILD_NUMBER} || true; docker network rm test-net-${BUILD_NUMBER} || true"
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) {
                    sh '''
                        echo "Desplegando en ${BRANCH_NAME}..."
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
                            
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
}

def branchIP() {
    return (env.BRANCH_NAME == 'main') ? '3.144.231.64' : '18.219.33.101'
}

def branchPort() {
    return (env.BRANCH_NAME == 'main') ? '8071' : '8070'
}